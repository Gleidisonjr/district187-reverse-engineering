// =====================================================================
//  GUNCELLEYICI - dosya karsilastirma ve indirme motoru.
//
//  BU DOSYA NE YAPAR (tamami bu kadar):
//    1. Sunucudan manifest.json indirir  (dosya listesi + SHA-256'lari)
//    2. Oyun klasorundeki dosyalarin SHA-256'sini hesaplar
//    3. Farkli/eksik olanlari  <kaynak>/objects/<sha256>  adresinden indirir
//    4. Once .indiriliyor uzantisiyla yazar, hash'i DOGRULAR, sonra yerine tasir
//    5. Onceki surumde kurulup artik listede olmayan dosyalari siler
//
//  NE YAPMAZ:
//    * Kayit defterine (registry) DOKUNMAZ
//    * Oyun klasorunun DISINA tek bayt yazmaz
//    * Hicbir seyi calistirmaz (oyunu baslatan kisim AnaPencere.cs'te,
//      ve yalnizca yapilandirmada yazan exe'yi calistirir)
//    * Makineden bilgi TOPLAMAZ, hicbir yere veri GONDERMEZ.
//      Tek ag trafigi: yapilandirmadaki adresten GET istekleri.
// =====================================================================
using System;
using System.Threading;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace S2Launcher
{
    /// <summary>Manifestteki tek bir dosya kaydi.</summary>
    public class DosyaKaydi
    {
        public string Yol;      // oyun klasorune GORE yol, ornek: "Game/GameClient.dll"
        public string Sha256;
        public long Boyut;
    }

    public class Manifest
    {
        public string Surum = "";
        public List<DosyaKaydi> Dosyalar = new List<DosyaKaydi>();
        // Bu dosyalara ASLA dokunulmaz (oyuncunun kendi ayarlari).
        public List<string> Korunan = new List<string>();
    }

    /// <summary>Yapilacak tek is: indir ya da sil.</summary>
    public class Is
    {
        public string Yol;
        public string Sha256;
        public long Boyut;
        public bool Silinecek;
    }

    public class Ilerleme
    {
        public string Durum = "";
        public long Yapilan;
        public long Toplam;
        public int DosyaSirasi;
        public int DosyaSayisi;
    }

    public class Guncelleyici
    {
        string _kaynak;                // ETKIN adres, ornek: https://cdn.ornek.com
        readonly string _yedek;        // ana adres cevap vermezse gecilecek adres
        bool _yedegeGecildi;
        readonly string _oyunKlasoru;
        readonly Action<Ilerleme> _bildir;
        readonly JavaScriptSerializer _js = new JavaScriptSerializer();

        // Hash onbellegi: ayni dosyayi her aciliste yeniden hashlemeyelim.
        // 1.2 GB'i hashlemek diskten ~15 sn surer; onbellekle ~0 sn.
        Dictionary<string, OnbellekSatiri> _onbellek = new Dictionary<string, OnbellekSatiri>();

        class OnbellekSatiri { public long Boyut; public long Zaman; public string Sha256; }

        /// <summary>Launcher'in kendisi guncellendiyse true olur.</summary>
        public bool LauncherYenilendi;

        /// <summary>
        /// `launcher.cfg` guncellendiyse true olur.
        ///
        /// NEDEN VAR (24.08.2026): launcher ayarlari acilista BIR KEZ okuyup
        /// bellekte tutuyor (`AnaPencere._ayar`), oyunu da o nesneden kurdugu
        /// komut satiriyla aciyor ("+gs_ip", Ip). Guncelleme yeni cfg'yi
        /// DISKE yaziyor ama calisan launcher eski degerlerle devam ediyordu:
        /// oyuncu guncellemeyi alip launcher'i KAPATMADAN Baslat'a basinca
        /// ESKI sunucu adresine gidiyordu. Sunucu tasindigi gun bu
        /// "guncelledim ama yine eski sunucuya baglaniyor" demek.
        ///
        /// Cozum, launcher'in kendi exe'si yenilendiginde zaten yapilan sey:
        /// KENDINI YENIDEN BASLAT. Bellekte tek alan tazelemek yeterli
        /// degildi - cfg'ye bagli baska durum da var (kaynak adresleri,
        /// gorseller, dil secimi) ve hepsini elle tazelemek eksik kalmaya
        /// aciktir.
        /// </summary>
        public bool AyarYenilendi;

        /// <summary>Yeniden baslatma gerektiren bir dosya yenilendi mi.</summary>
        public bool YenidenBaslatmaGerek
        {
            get { return LauncherYenilendi || AyarYenilendi; }
        }

        /// <summary>
        /// TAM DENETIM. Normalde hash onbellegi kullanilir: dosyanin boyutu ve
        /// degistirilme tarihi ayniysa yeniden hashlenmez (1.09 GB'i her
        /// aciliste hashlemek ~15 sn surerdi). Bu iyi bir hizlandirma ama
        /// KASITLI bozulmayi kacirir: biri dosyayi ayni boyutta degistirip
        /// tarihi geri alirsa onbellek "degismemis" der.
        /// Bu bayrak acikken onbellek TAMAMEN yok sayilir ve her dosya
        /// bastan hashlenir. Yavas ama kesin.
        /// </summary>
        public bool TamDenetim;

        /// <summary>
        /// Tam denetimde: korunan (ustune yazilmayan) dosyalardan resmi
        /// surumden FARKLI olanlar. Onarilmazlar - sadece raporlanirlar,
        /// cunku oyuncunun kendi ayari/ozellestirmesi olabilirler.
        /// </summary>
        public List<string> KorunanFarkli = new List<string>();

        /// <summary>
        /// Toplu silme korumasi devreye girdiyse, engellenen silme sayisi.
        /// 0 = normal. Sifirdan buyukse manifest supheli demektir.
        /// </summary>
        public int TopluSilmeEngellendi;

        /// <summary>
        /// TAM DENETIMDE bulunan YABANCI dosyalar: oyun klasorunde duran ama
        /// (a) manifestte olmayan, (b) korunan listesinde olmayan, (c) bu
        /// launcher'in kurmadigi dosyalar.
        ///
        /// NEDEN GEREKLI: silme mantigi yalnizca KENDI kurdugu dosyalari
        /// aday sayiyor (`KuruluListeOku`). Disaridan klasore atilan bir
        /// dosya ne fark ediliyor ne siliniyordu; rapordaki
        /// "Silinen (fazla): 0" satiri "fazla dosya yok" gibi okunuyordu,
        /// oysa anlami "kurduklarimin arasinda fazla yok" idi.
        ///
        /// SILMIYORUZ, yalnizca BILDIRIYORUZ: oyuncunun kendi ekran
        /// goruntusu, mod'u ya da yedegi olabilir. Karar oyuncunun.
        /// </summary>
        public List<string> YabanciDosyalar = new List<string>();

        // Yabanci taramasinda YOK SAYILAN klasorler: calisma zamani ciktisi
        // ve launcher'in kendi defteri. Bunlar zaten hicbir zaman yayinlanmaz.
        static readonly string[] YABANCI_MUAF_KLASOR = { "devlog/", ".launcher/", "profiles/" };
        static readonly string[] YABANCI_MUAF_UZANTI = { ".log", ".dmp", ".tmp", ".indiriliyor" };

        /// <summary>
        /// BASKA bir kaynagin kurdugu, bu manifeste ait OLMAYAN dosyalar.
        /// Yabanci taramasinda yok sayilirlar.
        ///
        /// NEDEN: HD grafik paketi ayri bir depodan (ayri manifest, ayri
        /// imza) iniyor. Standart guncelleyici `Game/HD.Res00`'i kendi
        /// listesinde goremedigi icin "yabanci dosya" diye raporlardi.
        /// Ana pencere HD listesini buraya verip sustururyor.
        /// </summary>
        public List<string> EkMuaf = new List<string>();

        /// <summary>
        /// Bu calistirmada TAMAMEN yok sayilacak yollar: indirilmez, silinmez,
        /// yabanci sayilmaz.
        ///
        /// NEDEN: Ingilizce dil paketi `Game/StringDatabase/Turkey/TheRaw.Strdb00p`
        /// dosyasinin UZERINE yaziyor - oyun dil klasorunu sabit okuyor, baska
        /// yere koyulamiyor. Ama ayni yol STANDART manifestte de var. Dil paketi
        /// seciliyken standart guncelleyici her aciliste "hash tutmuyor" deyip
        /// Turkcesini geri indirirdi; dil asamasi da hemen ardindan Ingilizcesini
        /// geri yazardi. Sonsuz bir gidip gelme, her aciliste bosuna 300 KB.
        ///
        /// `Korunan` ile YAPILAMAZ: o liste manifestten geliyor ve sunucudaki
        /// herkes icin ayni; bu ise yalnizca dil paketi SECILI oyuncuda gecerli.
        /// </summary>
        public List<string> Atla = new List<string>();

        bool Atlanir(string yol)
        {
            for (int i = 0; i < Atla.Count; i++)
                if (string.Equals(Atla[i], yol, StringComparison.OrdinalIgnoreCase)) return true;
            return false;
        }

        /// <summary>
        /// Durum dosyalarinin ek adi. Bos = standart depo
        /// (`.launcher\kurulu.json`), "hd" = HD deposu
        /// (`.launcher\kurulu-hd.json`).
        ///
        /// SART: iki guncelleyici ayni klasore calisiyor. Tek deftere
        /// yazsalardi her biri digerinin dosyalarini "artik listede yok"
        /// sayip SILERDI.
        /// </summary>
        public string Etiket = "";

        /// <summary>
        /// SIFIRDAN KURULUM. Acikken:
        ///   * `Korunan` listesi YOK SAYILIR - settings.cfg, profil, launcher.cfg
        ///     dahil her dosya sunucudaki surumle degistirilir,
        ///   * onbellek yok sayilir, her dosyanin hash'i bastan hesaplanir.
        ///
        /// "Oyunu yeniden kur" dugmesi bunu kullanir. Oyuncunun ayarlari
        /// GIDER - o yuzden dugme acik acik uyariyor ve onay istiyor.
        /// </summary>
        public bool ZorlaHepsi;

        public Guncelleyici(string kaynak, string oyunKlasoru, Action<Ilerleme> bildir)
            : this(kaynak, null, oyunKlasoru, bildir) { }

        /// <summary>
        /// `yedekKaynak` verilirse, ana adres 4 denemede de yanit vermezse
        /// otomatik olarak ona gecilir. Alan adi degistirmeyi RISKSIZ yapar:
        /// eski adres bir sure acik tutulur, kimse ortada kalmaz.
        /// </summary>
        public Guncelleyici(string kaynak, string yedekKaynak, string oyunKlasoru,
                            Action<Ilerleme> bildir)
        {
            _yedek = string.IsNullOrEmpty(yedekKaynak) ? null : yedekKaynak.TrimEnd('/');
            _kaynak = kaynak.TrimEnd('/');
            _oyunKlasoru = oyunKlasoru;
            _bildir = bildir;
            _js.MaxJsonLength = 64 * 1024 * 1024;
            // Cloudflare ve cogu CDN artik yalniz TLS 1.2+ kabul ediyor.
            // .NET Framework varsayilani eski oldugu icin ACIKCA sectik.
            ServicePointManager.SecurityProtocol =
                SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11;
            // 100-Continue beklemek bazi vekil sunucularda istegi asiyor.
            ServicePointManager.Expect100Continue = false;
            // Varsayilan sunucu basina 2 baglanti; indirmeler sirali oldugu
            // icin sart degil ama bagli kalan soketlerin sirayi tikamasini
            // onluyor.
            if (ServicePointManager.DefaultConnectionLimit < 8)
                ServicePointManager.DefaultConnectionLimit = 8;
        }

        // ---------------------------------------------------------------
        //  AG DAYANIKLILIGI
        //
        //  NEDEN: guncelleme kaynagi Cloudflare R2'nin `pub-*.r2.dev`
        //  gelistirme adresi ve Cloudflare bu adresi ACIKCA hiz sinirliyor
        //  (uretim trafigi icin ozel alan adi onerilir). Ustune oyuncunun
        //  kendi hattinda anlik bir kopma da yeter.
        //
        //  ONCEDEN: `MetinIndir`/`DosyaIndir` TEK denemeydi. Tek bir anlik
        //  hata tum guncellemeyi dusuruyordu ve oyuncu su kutuyu goruyordu:
        //      "Guncelleme yapilamadi: Temel alinan baglanti kapatildi..."
        //  (.NET'in `WebException` metni). Oyun acilmiyordu.
        //
        //  SIMDI: ag hatalarinda artan bekleme ile 4 deneme. Kalici hata
        //  (404, disk dolu, hash tutmamasi) yine ANINDA yukari firlar -
        //  yalnizca AG hatalari tekrarlanir.
        // ---------------------------------------------------------------
        const int AG_DENEME = 4;

        static bool GeciciAgHatasi(Exception ex)
        {
            var w = ex as WebException;
            if (w == null) return false;
            // Sunucu "yok" diyorsa tekrar denemek anlamsiz.
            var yanit = w.Response as HttpWebResponse;
            if (yanit != null)
            {
                int kod = (int)yanit.StatusCode;
                if (kod == 404 || kod == 403 || kod == 401) return false;
                // 429 (cok istek) ve 5xx tekrar denemeye DEGER.
                return kod == 429 || kod >= 500;
            }
            // Yanit yoksa: baglanti koptu / zaman asimi / DNS - tekrarlanabilir.
            return true;
        }

        /// <summary>
        /// Oyun klasorunu gezip manifestte OLMAYAN, korunmayan ve bu
        /// launcher'in kurmadigi dosyalari `YabanciDosyalar`a yazar.
        /// Yalnizca TAM DENETIMDE calisir (her aciliste diski gezmek gereksiz).
        /// </summary>
        void YabancilariTara(Manifest m, HashSet<string> listede, List<string> kurulu)
        {
            YabanciDosyalar.Clear();
            var kuruluKume = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (string k in kurulu) kuruluKume.Add(k);

            string[] hepsi;
            try { hepsi = Directory.GetFiles(_oyunKlasoru, "*", SearchOption.AllDirectories); }
            catch { return; }   // erisim hatasi: denetimi bozmayalim

            foreach (string tam in hepsi)
            {
                string gorece = tam.Substring(_oyunKlasoru.Length).TrimStart('\\', '/')
                                   .Replace('\\', '/');
                string kucuk = gorece.ToLowerInvariant();

                if (listede.Contains(gorece)) continue;          // resmi dosya
                if (Atlanir(gorece)) continue;                   // baska kaynagin sahibi
                if (m.Korunan.Contains(kucuk)) continue;         // oyuncunun kendi ayari
                if (kuruluKume.Contains(gorece)) continue;       // eski surumden kalma, silme mantigi ilgilenir

                bool muaf = false;
                // Baska kaynagin (HD deposu) kurdugu dosyalar: bizim
                // manifestimizde yoklar ama YABANCI da degiller.
                foreach (string k in EkMuaf)
                    if (string.Equals(k, gorece, StringComparison.OrdinalIgnoreCase)) { muaf = true; break; }
                if (!muaf)
                    foreach (string k in YABANCI_MUAF_KLASOR)
                        if (kucuk.StartsWith(k)) { muaf = true; break; }
                if (!muaf)
                    foreach (string u in YABANCI_MUAF_UZANTI)
                        if (kucuk.EndsWith(u)) { muaf = true; break; }
                // Kaynak klasoru korunan listesinde zaten var ama alt dosyalari
                // eklenmemis olabilir - komple muaf tut.
                if (!muaf && kucuk.StartsWith("acik-kaynak-launcher/")) muaf = true;
                if (muaf) continue;

                YabanciDosyalar.Add(gorece);
            }
            YabanciDosyalar.Sort(StringComparer.OrdinalIgnoreCase);
        }

        void Durum(string metin)
        {
            if (_bildir != null) _bildir(new Ilerleme { Durum = metin });
        }

        T AgDene<T>(Func<T> is_)
        {
            Exception son = null;
            // Dis dongu: once ANA adres, tukenirse YEDEK adres.
            while (true)
            {
                for (int deneme = 1; deneme <= AG_DENEME; deneme++)
                {
                    try { return is_(); }
                    catch (Exception ex)
                    {
                        if (!GeciciAgHatasi(ex)) throw;   // 404/403 gibi kalici hata: aninda yukari
                        son = ex;
                        if (deneme < AG_DENEME)
                        {
                            Durum(AnaPencere.S("Bağlantı koptu, yeniden deneniyor (", "Connection lost, retrying (")
                                  + deneme + "/" + (AG_DENEME - 1) + ")...");
                            Thread.Sleep(600 * deneme);   // 0.6s, 1.2s, 1.8s
                        }
                    }
                }

                // Ana adres tukendi - yedek varsa ona gec ve bastan dene.
                if (_yedek != null && !_yedegeGecildi)
                {
                    _yedegeGecildi = true;
                    _kaynak = _yedek;
                    Durum(AnaPencere.S("Ana sunucuya ulaşılamadı, yedek adrese geçiliyor...", "Main server unreachable, switching to the backup address..."));
                    continue;
                }
                break;
            }

            throw new Exception(
                AnaPencere.S("Sunucuya ", "Could not reach the server after ") + AG_DENEME + AnaPencere.S(" denemede de ulaşılamadı. İnternet bağlantınızı ", " attempts. Please check your internet connection ")
                + AnaPencere.S("kontrol edip tekrar deneyin. (", "and try again. (") + (son == null ? "?" : son.Message) + ")", son);
        }

        string DurumKlasoru { get { return Path.Combine(_oyunKlasoru, ".launcher"); } }

        // ---------------------------------------------------------------
        //  MANIFEST
        // ---------------------------------------------------------------
        // =================================================================
        //  MANIFEST IMZASI
        //
        //  NEDEN: launcher, sunucudan gelen `manifest.json`a KOSULSUZ
        //  guveniyordu. HTTPS tasimayi korur ama depoyu ele geciren biri
        //  sahte hash'lerle manifest yayinlarsa launcher onlari "onarim"
        //  diye indirip oyun klasorune yazardi. Guven zincirinin bu halkasi
        //  kriptografik olarak bagli degildi.
        //
        //  SIMDI: yayinci `manifest.json`i RSA-2048 + SHA-256 ile imzalayip
        //  `manifest.sig` (base64) olarak yaniyor koyar. Asagidaki ACIK
        //  anahtar bu programa GOMULU - yani imzayi dogrulayan sey sunucudan
        //  gelen bir sey degil, elinizdeki exe.
        //
        //  Acik anahtarin burada duz metin olmasi KASITLI: kodu okuyan
        //  herkes hangi anahtara guvenildigini gorebilir. Gizli anahtar
        //  yalnizca yayinci makinesindedir ve HICBIR ZAMAN yayinlanmaz.
        //
        //  Imza yoksa ya da tutmuyorsa guncelleme BASLAMAZ. Bilerek katiyiz:
        //  dogrulanmamis bir listeye gore oyun klasorune yazmak, hic
        //  guncellememekten kotudur.
        // =================================================================
        const string ACIK_ANAHTAR_XML =
            "<RSAKeyValue><Modulus>rx6URa1fz5c7rOpwhk/YSEWCDRVh18UX+6z0a29aAiJWj6Z/uxLzQkGskK+CCqFDPp6oVpbLkB2BMbvyX5axIgCzg8+86wiE7VOWCb4rp5yY2nxPI3A/tBFUKOJdvftdDxIpH2wsF7Md7gPkyy2E0ILLrvu9oFXF6HwRrr+i98jBvOPVjmIV1MCpryHMrIXSXvnIEJc+xWhH5CuQ3EofdxhoncXZI80/cttNuMI70aPoSRcA/6Oej8GDnzCeb7CY73N2e059a1NcFQrEFUXbIZ68ghYUVi3QbQ747SHygimZ+d5y94ESjSskqS331T9UZdcxfXyUBjOGWe7iK/alew==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>";

        void ImzaDogrula(string manifestHam)
        {
            if (ACIK_ANAHTAR_XML.StartsWith("<!--"))
                return;                       // anahtar henuz gomulmemis (gecis surumu)

            string imzaB64;
            try { imzaB64 = MetinIndir("/manifest.sig").Trim(); }
            catch (Exception ex)
            {
                throw new Exception(
                    AnaPencere.S("Sürüm listesinin imzası alınamadı; güncelleme durduruldu. (", "The version list signature could not be fetched; update stopped. (")
                    + ex.Message + ")", ex);
            }

            byte[] imza;
            try { imza = Convert.FromBase64String(imzaB64); }
            catch { throw new Exception(AnaPencere.S("Sürüm listesinin imzası bozuk; güncelleme durduruldu.", "The version list signature is corrupt; update stopped.")); }

            using (var rsa = new RSACryptoServiceProvider())
            {
                rsa.PersistKeyInCsp = false;
                rsa.FromXmlString(ACIK_ANAHTAR_XML);
                bool tamam;
                using (var sha = SHA256.Create())
                    tamam = rsa.VerifyData(Encoding.UTF8.GetBytes(manifestHam), sha, imza);
                if (!tamam)
                    throw new Exception(
                        AnaPencere.S("Sürüm listesinin imzası DOĞRULANAMADI. Güncelleme durduruldu ve ", "The version list signature COULD NOT BE VERIFIED. The update was stopped and ")
                        + AnaPencere.S("oyununuza dokunulmadı. Bu, dosyaların beklenen kaynaktan ", "your game was left untouched. It means the files did not come from ")
                        + AnaPencere.S("gelmediği anlamına gelir.", "the expected source."));
            }
        }

        public Manifest ManifestIndir()
        {
            Duyur(AnaPencere.S("Sürüm bilgisi alınıyor...", "Fetching version information..."), 0, 1);
            string ham = MetinIndir("/manifest.json");
            ImzaDogrula(ham);
            var kok = (Dictionary<string, object>)_js.DeserializeObject(ham);

            var m = new Manifest();
            if (kok.ContainsKey("surum")) m.Surum = Convert.ToString(kok["surum"]);

            if (kok.ContainsKey("dosyalar"))
            {
                foreach (var oge in (object[])kok["dosyalar"])
                {
                    var d = (Dictionary<string, object>)oge;
                    m.Dosyalar.Add(new DosyaKaydi
                    {
                        Yol = Convert.ToString(d["yol"]).Replace('\\', '/'),
                        Sha256 = Convert.ToString(d["sha256"]).ToLowerInvariant(),
                        Boyut = Convert.ToInt64(d["boyut"])
                    });
                }
            }
            if (kok.ContainsKey("korunan"))
                foreach (var oge in (object[])kok["korunan"])
                    m.Korunan.Add(Convert.ToString(oge).Replace('\\', '/').ToLowerInvariant());
            // Bos manifest = bozuk/yarim inmis. Devam edilirse silme kurali
            // tum kurulumu siler. Burada durduruyoruz.
            if (m.Dosyalar.Count == 0)
                throw new Exception(AnaPencere.S("Sunucudan gelen dosya listesi boş. ", "The file list from the server is empty. ")
                    + AnaPencere.S("Güncelleme iptal edildi (oyununuza dokunulmadı).", "Update cancelled (your game was left untouched)."));
            return m;
        }

        // ---------------------------------------------------------------
        //  FARKI CIKAR
        // ---------------------------------------------------------------
        public List<Is> FarkiCikar(Manifest m)
        {
            OnbellekYukle();
            var isler = new List<Is>();
            var listede = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            int sira = 0;
            foreach (var d in m.Dosyalar)
            {
                sira++;
                listede.Add(d.Yol);
                Duyur("Dosyalar denetleniyor...", sira, m.Dosyalar.Count);

                string tam = Path.Combine(_oyunKlasoru, d.Yol.Replace('/', '\\'));

                // ATLA = baska bir kaynak (dil paketi) bu yolun sahibi.
                // Indirme de silme de yok; yabanci taramasi da gormesin.
                if (Atlanir(d.Yol)) continue;

                // KORUNAN = oyuncunun kendi ayari (cozunurluk, tuslar, profil).
                // YOKSA kurulur, VARSA bir daha ASLA dokunulmaz. Aksi halde her
                // guncelleme oyuncunun ayarlarini sifirlar; ustelik oyun bu
                // dosyalari her cikista yeniden yazdigi icin hash hicbir zaman
                // tutmaz ve dosya her aciliste bosuna indirilirdi.
                // ZorlaHepsi -> korunan kuralini atla, dosyayi da bastan indir.
                if (!ZorlaHepsi && m.Korunan.Contains(d.Yol.ToLowerInvariant()))
                {
                    if (!File.Exists(tam))
                        isler.Add(new Is { Yol = d.Yol, Sha256 = d.Sha256, Boyut = d.Boyut });
                    else if (TamDenetim && HashHesapla(tam) != d.Sha256)
                        KorunanFarkli.Add(d.Yol);   // onarma - yalnizca bildir
                    continue;
                }

                if (!File.Exists(tam))
                {
                    isler.Add(new Is { Yol = d.Yol, Sha256 = d.Sha256, Boyut = d.Boyut });
                    continue;
                }
                if (ZorlaHepsi || YerelHash(tam, d.Yol) != d.Sha256)
                    isler.Add(new Is { Yol = d.Yol, Sha256 = d.Sha256, Boyut = d.Boyut });
            }
            OnbellekKaydet();

            // ---------------------------------------------------------------
            //  SILME + TOPLU SILME KORUMASI
            //
            //  Onceki surumde BIZIM kurdugumuz ama artik listede olmayan
            //  dosyalar silinir. Yalnizca kendi kurduklarimiza dokunuruz -
            //  oyuncunun kendi ekledigi hicbir dosya silinmez.
            //
            //  AMA: bozuk ya da yarim inmis bir manifest "hicbir dosya yok"
            //  demeye gelir ve bu kural TUM KURULUMU SILER. Gercekten yasandi
            //  (2026-08-12, test sirasinda 1 GB silindi). O yuzden iki kapi:
            //
            //    1. Manifest bos ise guncelleme hic baslamaz.
            //    2. Silinecek dosya sayisi kurulu listenin dortte birinden
            //       fazlaysa SILME ATLANIR. Fazladan dosya kalmasi zararsiz;
            //       kurulumun silinmesi degil.
            //
            //  Iki surum arasinda normal dosya cikarma zaten bu esiklerin
            //  altinda kalir, dolayisiyla normal akis etkilenmez.
            // ---------------------------------------------------------------
            var kurulu = KuruluListeOku();
            var silinecekler = new List<Is>();
            foreach (string eski in kurulu)
            {
                if (listede.Contains(eski)) continue;
                if (Atlanir(eski)) continue;
                if (m.Korunan.Contains(eski.ToLowerInvariant())) continue;
                if (File.Exists(Path.Combine(_oyunKlasoru, eski.Replace('/', '\\'))))
                    silinecekler.Add(new Is { Yol = eski, Silinecek = true });
            }

            if (silinecekler.Count > 10 && silinecekler.Count > kurulu.Count / 4)
            {
                TopluSilmeEngellendi = silinecekler.Count;
                // Silmeleri ekleme - indirmeler yine de yapilsin.
            }
            else
            {
                isler.AddRange(silinecekler);
            }

            if (TamDenetim) YabancilariTara(m, listede, kurulu);
            return isler;
        }

        // ---------------------------------------------------------------
        //  UYGULA
        // ---------------------------------------------------------------
        public void Uygula(List<Is> isler, Manifest m)
        {
            long toplam = 0;
            foreach (var i in isler) if (!i.Silinecek) toplam += i.Boyut;
            long yapilan = 0;
            int sira = 0;

            foreach (var i in isler)
            {
                sira++;
                string tam = Path.Combine(_oyunKlasoru, i.Yol.Replace('/', '\\'));

                if (i.Silinecek)
                {
                    Duyur("Eskiyen dosya siliniyor: " + i.Yol, yapilan, toplam, sira, isler.Count);
                    try { File.Delete(tam); } catch { }
                    continue;
                }

                Directory.CreateDirectory(Path.GetDirectoryName(tam));
                string gecici = tam + ".indiriliyor";

                long busu = yapilan;
                DosyaIndir("/objects/" + i.Sha256, gecici, i.Boyut,
                    delegate(long okunan)
                    {
                        Duyur(AnaPencere.S("İndiriliyor: ", "Downloading: ") + i.Yol, busu + okunan, toplam, sira, isler.Count);
                    });

                // DOGRULAMA: indirilen sey gercekten beklenen dosya mi?
                // Tutmuyorsa oyun klasorune HIC dokunmuyoruz.
                string geldi = HashHesapla(gecici);
                if (geldi != i.Sha256)
                {
                    try { File.Delete(gecici); } catch { }
                    throw new Exception(AnaPencere.S("Doğrulama başarısız: ", "Verification failed: ") + i.Yol
                        + AnaPencere.S("\nBeklenen ", "\nExpected ") + i.Sha256.Substring(0, 12)
                        + AnaPencere.S(", gelen ", ", got ") + geldi.Substring(0, 12));
                }

                // Calisan launcher'in kendisi guncelleniyorsa uzerine YAZILAMAZ.
                // Windows calisan bir exe'yi SILDIRMEZ ama YENIDEN ADLANDIRTIR.
                // Bu yuzden: eskisini .eski yap, yenisini yerine koy.
                // (Kalan .eski dosyasi bir sonraki aciliste temizlenir.)
                if (KendiExeMi(tam))
                {
                    string eski = tam + ".eski";
                    try { if (File.Exists(eski)) File.Delete(eski); } catch { }
                    File.Move(tam, eski);
                    File.Move(gecici, tam);
                    LauncherYenilendi = true;
                }
                else
                {
                    if (File.Exists(tam)) File.Delete(tam);
                    File.Move(gecici, tam);
                    // Ayar dosyasi yenilendiyse calisan launcher'in bellegi
                    // bayat kaldi - AnaPencere bunu gorup kendini yeniden
                    // baslatiyor. Karsilastirma manifestteki yol uzerinden;
                    // ayirici olarak hem '/' hem '\' kabul ediliyor.
                    if (string.Equals(i.Yol.Replace('\\', '/'), "launcher.cfg",
                                      StringComparison.OrdinalIgnoreCase))
                    {
                        AyarYenilendi = true;
                    }
                }
                yapilan += i.Boyut;
                OnbellekGuncelle(tam, i.Yol, i.Sha256);
            }

            OnbellekKaydet();
            KuruluListeYaz(m);
        }

        static bool KendiExeMi(string tam)
        {
            try
            {
                string ben = System.Reflection.Assembly.GetExecutingAssembly().Location;
                return !string.IsNullOrEmpty(ben)
                    && string.Equals(Path.GetFullPath(tam), Path.GetFullPath(ben),
                                     StringComparison.OrdinalIgnoreCase);
            }
            catch { return false; }
        }

        /// <summary>Onceki kendini-guncellemeden kalan .eski dosyasini siler.</summary>
        public static void ArtiklariTemizle()
        {
            try
            {
                string ben = System.Reflection.Assembly.GetExecutingAssembly().Location;
                if (!string.IsNullOrEmpty(ben) && File.Exists(ben + ".eski"))
                    File.Delete(ben + ".eski");
            }
            catch { }
        }

        // ---------------------------------------------------------------
        //  AG
        // ---------------------------------------------------------------
        // DIKKAT: bu iki yardimciya GORECE yol verilir ("/manifest.json").
        // Mutlak adres LAMBDANIN ICINDE kurulur ki yedek adrese gecildiginde
        // yeniden deneme YENI adrese gitsin.
        string MetinIndir(string yol)
        {
            return AgDene(delegate
            {
                string url = _kaynak + yol;
                var istek = (HttpWebRequest)WebRequest.Create(url + "?t=" + DateTime.UtcNow.Ticks);
                istek.UserAgent = "S2Launcher";
                istek.Timeout = 30000;
                using (var y = istek.GetResponse())
                using (var s = new StreamReader(y.GetResponseStream(), Encoding.UTF8))
                    return s.ReadToEnd();
            });
        }

        void DosyaIndir(string yol, string hedef, long boyut, Action<long> ilerle)
        {
            // Yeniden denemede dosya BASTAN yazilir (FileMode.Create), yani
            // yarim kalan indirme birikmez. Ilerleme cubugu deneme basina
            // sifirdan sayar - kisa bir geri sicrama normaldir.
            AgDene<object>(delegate
            {
                var istek = (HttpWebRequest)WebRequest.Create(_kaynak + yol);
                istek.UserAgent = "S2Launcher";
                istek.Timeout = 30000;
                istek.ReadWriteTimeout = 120000;
                using (var yanit = istek.GetResponse())
                using (var girdi = yanit.GetResponseStream())
                using (var cikti = new FileStream(hedef, FileMode.Create, FileAccess.Write,
                                                  FileShare.None, 1 << 20))
                {
                    byte[] tampon = new byte[1 << 20];
                    long okunanToplam = 0;
                    int n;
                    while ((n = girdi.Read(tampon, 0, tampon.Length)) > 0)
                    {
                        cikti.Write(tampon, 0, n);
                        okunanToplam += n;
                        ilerle(okunanToplam);
                    }
                }
                return null;
            });
        }

        // ---------------------------------------------------------------
        //  HASH + ONBELLEK
        // ---------------------------------------------------------------
        public static string HashHesapla(string yol)
        {
            using (var sha = SHA256.Create())
            using (var s = new FileStream(yol, FileMode.Open, FileAccess.Read,
                                          FileShare.ReadWrite, 1 << 20))
            {
                byte[] h = sha.ComputeHash(s);
                var sb = new StringBuilder(64);
                for (int i = 0; i < h.Length; i++) sb.Append(h[i].ToString("x2"));
                return sb.ToString();
            }
        }

        string YerelHash(string tam, string bagilYol)
        {
            var bilgi = new FileInfo(tam);
            OnbellekSatiri s;
            if (!TamDenetim
                && _onbellek.TryGetValue(bagilYol, out s)
                && s.Boyut == bilgi.Length
                && s.Zaman == bilgi.LastWriteTimeUtc.Ticks)
                return s.Sha256;

            string h = HashHesapla(tam);
            _onbellek[bagilYol] = new OnbellekSatiri
            {
                Boyut = bilgi.Length,
                Zaman = bilgi.LastWriteTimeUtc.Ticks,
                Sha256 = h
            };
            return h;
        }

        void OnbellekGuncelle(string tam, string bagilYol, string hash)
        {
            var b = new FileInfo(tam);
            _onbellek[bagilYol] = new OnbellekSatiri
            { Boyut = b.Length, Zaman = b.LastWriteTimeUtc.Ticks, Sha256 = hash };
        }

        /// <summary>`.launcher\<ad>.json` ya da etiketliyse `<ad>-<etiket>.json`.</summary>
        string DurumDosya(string ad)
        {
            string e = string.IsNullOrEmpty(Etiket) ? "" : "-" + Etiket;
            return Path.Combine(DurumKlasoru, ad + e + ".json");
        }

        void OnbellekYukle()
        {
            _onbellek = new Dictionary<string, OnbellekSatiri>();
            string y = DurumDosya("onbellek");
            if (!File.Exists(y)) return;
            try
            {
                var k = (Dictionary<string, object>)_js.DeserializeObject(File.ReadAllText(y));
                foreach (var c in k)
                {
                    var d = (Dictionary<string, object>)c.Value;
                    _onbellek[c.Key] = new OnbellekSatiri
                    {
                        Boyut = Convert.ToInt64(d["boyut"]),
                        Zaman = Convert.ToInt64(d["zaman"]),
                        Sha256 = Convert.ToString(d["sha256"])
                    };
                }
            }
            catch { _onbellek = new Dictionary<string, OnbellekSatiri>(); }
        }

        void OnbellekKaydet()
        {
            Directory.CreateDirectory(DurumKlasoru);
            var d = new Dictionary<string, object>();
            foreach (var c in _onbellek)
                d[c.Key] = new Dictionary<string, object> {
                    { "boyut", c.Value.Boyut }, { "zaman", c.Value.Zaman }, { "sha256", c.Value.Sha256 } };
            try { File.WriteAllText(DurumDosya("onbellek"), _js.Serialize(d)); }
            catch { }
        }

        public List<string> KuruluListeOku()
        {
            var liste = new List<string>();
            string y = DurumDosya("kurulu");
            if (!File.Exists(y)) return liste;
            try
            {
                foreach (var o in (object[])_js.DeserializeObject(File.ReadAllText(y)))
                    liste.Add(Convert.ToString(o).Replace('\\', '/'));
            }
            catch { }
            return liste;
        }

        void KuruluListeYaz(Manifest m)
        {
            Directory.CreateDirectory(DurumKlasoru);
            var liste = new List<string>();
            foreach (var d in m.Dosyalar) liste.Add(d.Yol);
            try { File.WriteAllText(DurumDosya("kurulu"), _js.Serialize(liste)); }
            catch { }
        }

        /// <summary>
        /// Bu kaynagin kurdugu her seyi siler ve defterini bosaltir.
        /// HD paketinden STANDART pakete donuste kullanilir.
        /// Yalnizca KENDI kurulu listesindeki dosyalara dokunur; standart
        /// kurulumdan tek dosya bile silinemez.
        /// </summary>
        public int HepsiniKaldir()
        {
            int n = 0;
            var klasorler = new List<string>();
            foreach (string bagil in KuruluListeOku())
            {
                string tam = Path.Combine(_oyunKlasoru, bagil.Replace('/', '\\'));
                try { if (File.Exists(tam)) { File.Delete(tam); n++; } }
                catch { }
                string d = Path.GetDirectoryName(tam);
                if (d != null && !klasorler.Contains(d)) klasorler.Add(d);
            }
            // BOSALAN KLASORLERI DE SIL. Yoksa ingilizce paket kaldirildiktan
            // sonra `Game\Interface\...` altinda 19 bos klasor kaliyor. Ikisi de
            // zarar veriyor: (a) oyuncunun klasoru cop topluyor, (b) yayin
            // araci "Game\Interface var" diye standart paketi uretmiyor.
            // ICTEN DISA sirala - once en derin klasor bosalsin.
            klasorler.Sort(delegate(string a, string b) { return b.Length.CompareTo(a.Length); });
            foreach (string d in klasorler)
            {
                string y = d;
                // Kendi kokunun disina TASMASIN ve yalnizca GERCEKTEN bos olani sil.
                while (y != null && y.Length > _oyunKlasoru.Length
                       && y.StartsWith(_oyunKlasoru, StringComparison.OrdinalIgnoreCase))
                {
                    try
                    {
                        if (!Directory.Exists(y)) { y = Path.GetDirectoryName(y); continue; }
                        if (Directory.GetFileSystemEntries(y).Length != 0) break;
                        Directory.Delete(y);
                    }
                    catch { break; }
                    y = Path.GetDirectoryName(y);
                }
            }
            try { if (File.Exists(DurumDosya("kurulu"))) File.Delete(DurumDosya("kurulu")); }
            catch { }
            try { if (File.Exists(DurumDosya("onbellek"))) File.Delete(DurumDosya("onbellek")); }
            catch { }
            return n;
        }

        // ---------------------------------------------------------------
        void Duyur(string durum, long yapilan, long toplam)
        { Duyur(durum, yapilan, toplam, 0, 0); }

        void Duyur(string durum, long yapilan, long toplam, int sira, int sayi)
        {
            if (_bildir == null) return;
            _bildir(new Ilerleme
            {
                Durum = durum,
                Yapilan = yapilan,
                Toplam = toplam,
                DosyaSirasi = sira,
                DosyaSayisi = sayi
            });
        }
    }
}
