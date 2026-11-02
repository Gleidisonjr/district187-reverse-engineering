// =====================================================================
//  ApexKanal.cs - ANTI-HILE RAPOR KOPRUSU
// =====================================================================
//
//  ---- NE YAPAR ---------------------------------------------------------
//
//  ApexGuard oyunun KENDI surecinde kosuyor ve bulgularini paylasimli
//  bellege yaziyor. Bu sinif o bellegi okuyup sunucuya tasiyor:
//
//      ApexGuard (oyun icinde)  --memcpy-->  paylasimli bellek
//                                                  |
//                                            BU SINIF (launcher)
//                                                  |  HTTP, toplu
//                                                  v
//                                              Sunucu -> defter -> panel
//
//  ---- NEDEN OYUN GONDERMIYOR ------------------------------------------
//
//  Oyun surecinde yapilan her ag/disk islemi kareyi bolebiliyor. Olculdu
//  (`AgIzi.cs` ve ApexGuard notlari): eski istemci gunlugu tam da bu
//  yuzden oyunu takliyordu. Bu tasarimda oyunun payi TEK memcpy - olculen
//  11 ns/kayit. Ag ve JSON isi launcher'da, yani AYRI SURECTE. Burasi
//  takilsa ya da olse oyun etkilenmez.
//
//  ---- ⚠⚠ ESLEME ACIK TUTULMAK ZORUNDA ---------------------------------
//
//  ApexGuard bir ihlal yakalayinca kaydi yaziyor ve HEMEN `ExitProcess`
//  cagiriyor (oyunu kapatiyor). Windows'ta paylasimli bellek SON TUTAMAK
//  kapaninca yok olur. Yani ihlal kaydinin hayatta kalmasi bizim tutamagi
//  ACIK TUTMAMIZA bagli - kapatirsak KANIT OYUNLA BIRLIKTE BUHARLASIR.
//
//  Bu yuzden `Bitir()` once SON KEZ OKUR, sonra gonderir, EN SON kapatir.
//  C++ tarafinda bu bir sozlesme maddesi olarak yaziliyor (apex_kanal.h).
//  Sinandi: `apex_kanal_sinav.cpp` - "yazan oldukten SONRA kayit okunabiliyor".
//
//  ---- ⚠ BU KANAL DELIL DEGIL, IHBAR ------------------------------------
//
//  Paylasimli bellegi oyuncu da acip sahte kayit yazabilir; makine onun.
//  Buradan gelen her sey SUPHE, kanit degil. Kesin kanit sunucunun kendi
//  gozcusunden gelir (istemciye hic guvenmeyen katman). Asil guc ikisinin
//  CELISKISINDE: istemci "temizim" derken sunucu telde imkansiz bir atis
//  hizi goruyorsa, o celiski tek basina anlamlidir.
//
//  ---- KOPRU GUNLUGU (15.09.2026) --------------------------------------
//
//  polkas vakasi: sunucu oda girisinde "kalp=54sn once (imzali)" dedi,
//  oyun calisiyordu, sonrasi kor - kopru hicbir yere yazmiyordu, sunucu da
//  kalp basina satir tutmuyor. "Gonderdi mi, ulasti mi, kanal acildi mi"
//  sorusu cevapsiz kaldi. Artik `%LOCALAPPDATA%\S2Rebirth\apex-kopru.log`
//  (DiscordVarlik ile ayni yer/desen, 200 KB tavan): kanal acilisi, nonce,
//  her BASARISIZ POST (HTTP kodu / zaman asimi), toparlanma, 60 sn'de bir
//  ozet, cikis sebebi. Oyuncu "atildim" derse dosyayi ister, bakariz.
//  Oyunun karesine dokunmaz: yazma launcher ipliginde, hata yutulur.
//
//  ---- ⚠ C# 5 --------------------------------------------------------
//
//  Derleyici `csc.exe v4.0.30319` (derle.cmd). String interpolation,
//  `nameof`, `?.`, ifade govdeli uye YOK. Rakam ayiraci (30_000) da yok.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

namespace S2Launcher
{
    /// <summary>ApexGuard paylasimli bellek kanalini okuyup sunucuya tasir.</summary>
    public sealed class ApexKanal
    {
        // ---- SOZLESME: apex_kanal.h ile BIREBIR ------------------------
        // Bu sabitler C++ tarafiyla eslesmek ZORUNDA. Biri degisirse
        // digeri de degismeli; `surum` alani uyumsuzlugu yakalar.
        const uint SIHIR = 0x52585041;   // 'APXR'
        const uint SURUM = 1;
        const int METIN_BOY = 232;
        const int SLOT = 256;
        const int KAYIT_BOY = 256;
        const int NONCE_BOY = 32;

        const int OFS_BASLIK = 0;
        const int OFS_GELEN = 64;
        const int OFS_HALKA = 128;
        const int KANAL_BOY = OFS_HALKA + SLOT * KAYIT_BOY;

        // Baslik alan ofsetleri (paketli yapi)
        const int B_SIHIR = OFS_BASLIK + 0;
        const int B_SURUM = OFS_BASLIK + 4;
        const int B_KAYIT_BOYU = OFS_BASLIK + 8;
        const int B_KAPASITE = OFS_BASLIK + 12;
        const int B_YAZ = OFS_BASLIK + 16;
        const int B_OKU = OFS_BASLIK + 24;
        const int B_DUSEN = OFS_BASLIK + 32;

        // Gelen (launcher -> apex)
        const int G_SURUM = OFS_GELEN + 0;
        const int G_GECERLILIK = OFS_GELEN + 8;
        const int G_NONCE = OFS_GELEN + 16;

        // Kayit alan ofsetleri (halka basindan)
        const int K_ZAMAN = 0;
        const int K_TUR = 8;
        const int K_KOD = 12;
        const int K_UZUNLUK = 16;
        const int K_METIN = 24;

        /// <summary>Kanal aramasi bu kadar surer; sonra pes edilir.</summary>
        const int BAGLANMA_TAVANI_MS = 90000;

        /// <summary>
        /// Iki gonderim arasi. 12.09.2026 (v4.2): 20 sn -> 5 sn. Sunucunun mac
        /// kapisi son 20 sn icinde imzali kalp atisi istiyor; ApexGuard 5 sn'de
        /// bir atiyor, launcher da 5 sn'de bir tasiyor ki pencereye 3-4 atis
        /// payi kalsin. Her gonderim yeni nonce getiriyor (apex-rapor.js
        /// (ip,pid) basina, oncekini de kabul ediyor). Sunucu hiz siniri
        /// (`apexIp`) buna gore genisletildi.
        /// </summary>
        const int GONDERIM_ARALIGI_MS = 5000;

        /// <summary>Tek istekte en fazla kayit - devasa govde uretmeyelim.</summary>
        const int GONDERIM_TAVANI = 400;

        readonly string _uc;
        readonly Process _oyun;
        readonly string _oyuncu;
        Thread _isParcacigi;
        volatile bool _dur;

        MemoryMappedFile _esleme;
        MemoryMappedViewAccessor _gorunum;

        readonly List<Dictionary<string, object>> _kuyruk = new List<Dictionary<string, object>>();

        // Gunluk sayaclari (KOPRU GUNLUGU notu)
        int _istekSayisi;          // basarili POST
        int _kalpSayisi;           // gonderilen kalp kaydi
        int _ardisikHata;          // ust uste basarisiz POST
        // 14.10.2026 KOPRU DURUMU: halkadan okunan kalp sayisi ve son kalp
        // okuma ani. Sunucuya her POST'ta `kopru` alaniyla gidiyor; "launcher
        // yasiyor ama kalp yok" vakasinda kanal mi kapali, ApexGuard mi
        // susmus, POST mu dusuyor - sunucu tarafinda ayirt edilebilsin.
        long _okunanKalp;
        DateTime _sonKalpOkuma = DateTime.MinValue;
        DateTime _sonOzet = DateTime.UtcNow;
        DateTime _ilkHata = DateTime.MinValue;
        static readonly object GunlukKilidi = new object();

        ApexKanal(string uc, Process oyun, string oyuncu)
        {
            _uc = uc;
            _oyun = oyun;
            _oyuncu = oyuncu == null ? "" : oyuncu;
        }

        /// <summary>
        /// `%LOCALAPPDATA%\S2Rebirth\apex-kopru.log` - DiscordVarlik.Gunluk ile
        /// ayni desen. 200 KB'yi asinca sifirdan baslar. Hicbir kosulda firlatmaz.
        /// </summary>
        static void Gunluk(string satir)
        {
            try
            {
                lock (GunlukKilidi)
                {
                    string klasor = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "S2Rebirth");
                    Directory.CreateDirectory(klasor);
                    string yol = Path.Combine(klasor, "apex-kopru.log");
                    if (File.Exists(yol) && new FileInfo(yol).Length > 200 * 1024) File.Delete(yol);
                    File.AppendAllText(yol, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + satir + "\r\n", Encoding.UTF8);
                }
            }
            catch { }
        }

        /// <summary>
        /// Kopru kurulacak mi? `Tani.Acik` ile birebir ayni desen.
        ///
        /// ⚠ BU YOKLAMA NEDEN VAR (08.09.2026 - K-392):
        ///   `AnaPencere` oyunu baslattiktan sonra launcher'in HAYATTA
        ///   KALIP kalmayacagina karar veriyor. O karar yalnizca `tani` ve
        ///   `discord` ozelliklerine bakiyordu; ikisi de kapaliyken
        ///   launcher `Close()` ediyor ve surec oluyordu.
        ///
        ///   Kopru LAUNCHER SURECINDE yasadigi icin bu, koprunun HIC
        ///   calismamasi demekti: `Basla` satirina ulasilmiyordu bile.
        ///   Canlida `tani` bos (K-391) ve `discord_uygulama` bos oldugu
        ///   icin bu tam olarak yasanan durumdu - anti-hile ihlali
        ///   yakaliyor, oyunu kapatiyor, ama sunucuya tek bayt gitmiyordu.
        ///
        ///   Sessiz bir arizaydi: her sey "calisiyor" gorunuyor, yalnizca
        ///   panel bos kaliyor. Yoklamanin ozelligin KENDI dosyasinda
        ///   durmasinin sebebi bu - ozellik eklenirken nobetci kosulunun
        ///   guncellenmesi unutulmasin.
        /// </summary>
        public static bool Etkin(Ayarlar a)
        {
            return a != null && !string.IsNullOrEmpty(a.Apex) && a.ApexGonder;
        }

        /// <summary>
        /// Kopruyu baslatir. HICBIR KOSULDA FIRLATMAZ - `AgIzi.Basla` ile ayni
        /// sozlesme. Basarisiz olursa null doner ve oyun raporsuz devam eder;
        /// anti-hile yine calisir, yalnizca sunucu gormez.
        /// </summary>
        public static ApexKanal Basla(string uc, Process oyun, string oyuncu)
        {
            try
            {
                if (string.IsNullOrEmpty(uc) || oyun == null) return null;
                Ipv4Zorla(uc);
                ApexKanal k = new ApexKanal(uc, oyun, oyuncu);
                Gunluk("basladi pid=" + k.OyunPid() + " uc=" + uc);
                k._isParcacigi = new Thread(k.Dongu);
                k._isParcacigi.IsBackground = true;   // cikisi asla engelleme
                k._isParcacigi.Priority = ThreadPriority.BelowNormal;
                k._isParcacigi.Start();
                return k;
            }
            catch { return null; }
        }

        // ---------------------------------------------------------------
        //  IPv4 ZORUNLU  (13.09.2026 - mac kapisi olcumu)
        //
        //  OLCULDU: s2rebirth.com'un AAAA kaydi var (Cloudflare) ve Turk Telekom
        //  gibi IPv6 dagitan hatlarda launcher'in kalp atisi POST'u IPv6 ile
        //  gidiyor (portal gunlugu: HayatBize61Tekme 2a00:1d34:..., Cengelk0y
        //  2a00:1d34:...). Oyun ise lobiye IPv4 ile bagli (95.10.95.17,
        //  85.100.67.243). Sunucunun mac kapisi kalbi ADRESE gore ariyor ->
        //  IPv6'dan gelen kalp IPv4 oyuncuyla eslesmiyor -> "kalp=YOK" ->
        //  ZORLA kipinde mesru oyuncu reddedildi (00:01-00:09 arasi 36 red).
        //
        //  Cozum: bu ucun ServicePoint'i (ayni sema+konak icin tek nesne)
        //  IPv4'e zorlaniyor. .NET, DNS'in verdigi adresleri sirayla dener;
        //  delegate IPv6 adres icin firlatinca o deneme dusup SIRADAKI (IPv4)
        //  adrese geciliyor (ServicePoint.ConnectSocketInternal adres basina
        //  try/catch). IPv4 icin `IPAddress.Any:0` = varsayilan baglama.
        //  Yalniz portal ucu etkilenir; CDN/Discord istekleri oldugu gibi.
        // ---------------------------------------------------------------
        static bool _ipv4Kuruldu;
        static void Ipv4Zorla(string uc)
        {
            if (_ipv4Kuruldu) return;
            try
            {
                ServicePoint sp = ServicePointManager.FindServicePoint(new Uri(uc));
                sp.BindIPEndPointDelegate = delegate (ServicePoint p, IPEndPoint uzak, int deneme)
                {
                    if (uzak.AddressFamily == AddressFamily.InterNetworkV6)
                        throw new InvalidOperationException("IPv4 zorunlu (mac kapisi adres eslesmesi)");
                    return new IPEndPoint(IPAddress.Any, 0);
                };
                _ipv4Kuruldu = true;
            }
            catch { }
        }

        /// <summary>
        /// Durdurur. ⚠ SIRA KRITIK: once SON KEZ OKU, sonra gonder, EN SON
        /// eslemeyi kapat. Ters sirada ihlal kaydi kaybolur (bkz. dosya basi).
        /// Firlatmaz.
        /// </summary>
        public void Bitir()
        {
            try
            {
                _dur = true;
                if (_isParcacigi != null) _isParcacigi.Join(6000);
            }
            catch { }
            try { SonBosaltVeGonder(); } catch { }
            try { EslemeyiKapat(); } catch { }
            Gunluk("bitti pid=" + OyunPid() + " istek=" + _istekSayisi + " kalp=" + _kalpSayisi + " kuyrukta=" + _kuyruk.Count);
        }

        // ---------------------------------------------------------------
        //  ANA DONGU
        // ---------------------------------------------------------------
        void Dongu()
        {
            DateTime baslangic = DateTime.UtcNow;
            DateTime sonGonderim = DateTime.UtcNow;

            while (!_dur)
            {
                try
                {
                    // 1) Kanal henuz yoksa aramaya devam.
                    //
                    // ⚠ OYUN KAPANDI DIYE HEMEN CIKMA: ApexGuard ihlalde
                    //   oyunu ONCE oldurup kaydi biraktigi icin, en degerli
                    //   kayit tam da surec olduktan SONRA okunuyor olabilir.
                    //   Once esleme kurulmus mu ona bakiyoruz.
                    if (_gorunum == null)
                    {
                        if (!EslemeyiAc())
                        {
                            bool sureDoldu = (DateTime.UtcNow - baslangic).TotalMilliseconds > BAGLANMA_TAVANI_MS;
                            if (sureDoldu || OyunBitti())
                            {
                                // ApexGuard hic yuklenmemis (proxy DLL degistirilmis?) ya da
                                // oyun kanal acilmadan kapandi - ikisi de sunucuda "kalp=YOK".
                                Gunluk(sureDoldu
                                    ? "kanal ACILAMADI (" + (BAGLANMA_TAVANI_MS / 1000) + " sn) pid=" + OyunPid() + " - ApexGuard yuklenmemis?"
                                    : "oyun kanal acilmadan kapandi pid=" + OyunPid());
                                return;
                            }
                            Thread.Sleep(1000);
                            continue;
                        }
                        Gunluk("kanal acildi pid=" + OyunPid() + " (" + (int)(DateTime.UtcNow - baslangic).TotalSeconds + " sn sonra)");
                        // v4.2: NONCE'U ONCEDEN AL. ApexGuard ilk kalp atisini
                        // (acilistan ~5 sn sonra) imzalayabilsin diye kanal
                        // acilir acilmaz bos bir rapor gonderilip cevaptaki
                        // nonce paylasimli bellege yazilir. Basarisizsa dert
                        // degil: ilk dolu gonderim de nonce getirir.
                        NonceOnAl();
                    }

                    // 2) Bekleyen kayitlari al.
                    Bosalt();

                    // 3) Zamani geldiyse ya da yeterince biriktiyse gonder.
                    bool zamaniGeldi = (DateTime.UtcNow - sonGonderim).TotalMilliseconds >= GONDERIM_ARALIGI_MS;
                    if (_kuyruk.Count > 0 && (zamaniGeldi || _kuyruk.Count >= GONDERIM_TAVANI))
                    {
                        Gonder();
                        sonGonderim = DateTime.UtcNow;
                    }

                    // 4) Oyun kapandiysa: SON kez oku, gonder, cik.
                    if (OyunBitti())
                    {
                        Bosalt();
                        Gonder();
                        Gunluk("oyun kapandi pid=" + OyunPid() + " - son gonderim yapildi, kuyrukta=" + _kuyruk.Count);
                        return;
                    }

                    // 5) 60 sn'de bir ozet - "kopru yasiyor muydu" sorusunun cevabi.
                    if ((DateTime.UtcNow - _sonOzet).TotalSeconds >= 60)
                    {
                        _sonOzet = DateTime.UtcNow;
                        Gunluk("ozet pid=" + OyunPid() + " istek=" + _istekSayisi + " kalp=" + _kalpSayisi
                             + " kuyrukta=" + _kuyruk.Count + (_ardisikHata > 0 ? " ARDISIK HATA=" + _ardisikHata : ""));
                    }
                }
                catch (Exception e)
                {
                    // Kopru hicbir kosulda oyunu ya da launcher'i etkilemez.
                    Gunluk("dongu hatasi: " + e.Message);
                }
                Thread.Sleep(1000);
            }
        }

        bool OyunBitti()
        {
            try { return _oyun != null && _oyun.HasExited; }
            catch { return false; }
        }

        // ---------------------------------------------------------------
        //  PAYLASIMLI BELLEK
        // ---------------------------------------------------------------
        bool EslemeyiAc()
        {
            try
            {
                int pid;
                try { pid = _oyun.Id; } catch { return false; }
                string ad = "Local\\ApexRing_" + pid.ToString();

                _esleme = MemoryMappedFile.OpenExisting(ad, MemoryMappedFileRights.ReadWrite);
                _gorunum = _esleme.CreateViewAccessor(0, KANAL_BOY, MemoryMappedFileAccess.ReadWrite);

                // Sozlesme dogrulamasi: yanlis surumle konusmak sessiz
                // veri bozulmasindan iyidir.
                uint sihir = _gorunum.ReadUInt32(B_SIHIR);
                uint surum = _gorunum.ReadUInt32(B_SURUM);
                uint kayitBoyu = _gorunum.ReadUInt32(B_KAYIT_BOYU);
                if (sihir != SIHIR || surum != SURUM || kayitBoyu != KAYIT_BOY)
                {
                    EslemeyiKapat();
                    return false;
                }
                return true;
            }
            catch
            {
                // Henuz olusmamis olabilir - cagiran tekrar dener.
                EslemeyiKapat();
                return false;
            }
        }

        void EslemeyiKapat()
        {
            try { if (_gorunum != null) _gorunum.Dispose(); } catch { }
            try { if (_esleme != null) _esleme.Dispose(); } catch { }
            _gorunum = null;
            _esleme = null;
        }

        /// <summary>Halkadaki tum yeni kayitlari kuyruga alir.</summary>
        void Bosalt()
        {
            if (_gorunum == null) return;
            byte[] tampon = new byte[METIN_BOY];

            while (true)
            {
                long oku = _gorunum.ReadInt64(B_OKU);
                long yaz = _gorunum.ReadInt64(B_YAZ);
                if (oku >= yaz) break;

                // ⚠ Cok geride kaldiysak (yazan ezmedi ama biz uyuduysak)
                //   yine de sirayla okuyoruz: yazan taraf DOLULUKTA YENIYI
                //   DUSURUYOR, eskiyi ezmiyor. Yani okudugumuz her kayit
                //   butun. Gerekce: apex_kanal.h "DOLUNCA ESKIYI EZME".
                int slot = (int)(oku & (SLOT - 1));
                int taban = OFS_HALKA + slot * KAYIT_BOY;

                ulong zaman = _gorunum.ReadUInt64(taban + K_ZAMAN);
                uint tur = _gorunum.ReadUInt32(taban + K_TUR);
                uint kod = _gorunum.ReadUInt32(taban + K_KOD);
                uint uzunluk = _gorunum.ReadUInt32(taban + K_UZUNLUK);
                if (uzunluk > METIN_BOY - 1) uzunluk = METIN_BOY - 1;
                _gorunum.ReadArray(taban + K_METIN, tampon, 0, (int)uzunluk);
                string metin = Encoding.UTF8.GetString(tampon, 0, (int)uzunluk);

                _gorunum.Write(B_OKU, oku + 1);        // tuketildi

                Dictionary<string, object> kayit = new Dictionary<string, object>();
                kayit["tur"] = TurAdi(tur);
                kayit["kod"] = kod;
                // ApexGuard'in BASLAMASINDAN beri gecen ms. Once makinenin
                // acilisindan beriydi ve panelde 6,9 GUN gibi degerler
                // cikiyordu (08.09.2026); gerekce apex_kanal.h `basTik`.
                kayit["acilistanMs"] = zaman;
                kayit["metin"] = metin;
                if (tur == 3) { _okunanKalp++; _sonKalpOkuma = DateTime.UtcNow; }
                _kuyruk.Add(kayit);

                if (_kuyruk.Count > GONDERIM_TAVANI * 4) break;   // guvenlik freni
            }
        }

        static string TurAdi(uint tur)
        {
            switch (tur)
            {
                case 1: return "ihlal";
                case 2: return "modul";
                case 3: return "kalp";
                case 4: return "bilgi";
                default: return "bilinmeyen";
            }
        }

        void SonBosaltVeGonder()
        {
            Bosalt();
            Gonder();
        }

        // ---------------------------------------------------------------
        //  SUNUCUYA GONDERIM
        // ---------------------------------------------------------------
        /// <summary>Bos rapor: yalniz nonce almak icin (v4.2). Firlatmaz.</summary>
        void NonceOnAl()
        {
            try { Gonder(true); } catch { }
        }

        void Gonder() { Gonder(false); }

        void Gonder(bool bosOlsaDa)
        {
            if (_kuyruk.Count == 0 && !bosOlsaDa) return;

            long dusen = 0;
            try { if (_gorunum != null) dusen = _gorunum.ReadInt64(B_DUSEN); } catch { }

            // Tavana kadar al; kalani sonraki tura biraksin.
            int adet = _kuyruk.Count < GONDERIM_TAVANI ? _kuyruk.Count : GONDERIM_TAVANI;
            List<Dictionary<string, object>> parca = _kuyruk.GetRange(0, adet);

            Dictionary<string, object> govde = new Dictionary<string, object>();
            govde["surum"] = 1;
            govde["oyuncu"] = _oyuncu;
            govde["pid"] = OyunPid();
            govde["gonderildi"] = DateTime.UtcNow.ToString("o");
            // ⚠ `dusen` SUNUCUYA SOYLENIYOR: kuyruk dolup kayit dustuyse
            //   "kanit eksik olabilir" demek gerekiyor. Sessizce eksik
            //   veri gondermek yanlis guven verir.
            govde["dusen"] = dusen;
            govde["kayitlar"] = parca;
            // 14.10.2026: KOPRU DURUMU (sunucu apex-rapor.js `kopru` olarak okur).
            //   kanal          esleme acik mi (ApexGuard halkasi bulundu mu)
            //   okunanKalp     bu surecte halkadan okunan toplam kalp
            //   sonKalpOkumaSn son kalp okumasindan bu yana saniye (-1 = hic)
            //   ardisikHata    ust uste dusen POST sayisi (bu istek oncesi)
            Dictionary<string, object> kopru = new Dictionary<string, object>();
            kopru["kanal"] = _gorunum != null;
            kopru["okunanKalp"] = _okunanKalp;
            kopru["sonKalpOkumaSn"] = _sonKalpOkuma == DateTime.MinValue ? -1 : (int)(DateTime.UtcNow - _sonKalpOkuma).TotalSeconds;
            kopru["ardisikHata"] = _ardisikHata;
            govde["kopru"] = kopru;

            int kalpAdedi = 0;
            for (int i = 0; i < parca.Count; i++)
            {
                object t;
                if (parca[i].TryGetValue("tur", out t) && "kalp".Equals(t as string)) kalpAdedi++;
            }

            string cevap = null;
            try
            {
                ServicePointManager.SecurityProtocol =
                    SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11;

                string json = new JavaScriptSerializer().Serialize(govde);
                using (WebClient wc = new KisaZamanAsimliWebClient())
                {
                    wc.Headers[HttpRequestHeader.ContentType] = "application/json";
                    wc.Headers[HttpRequestHeader.UserAgent] = "S2Launcher";
                    wc.Encoding = Encoding.UTF8;
                    cevap = wc.UploadString(_uc, "POST", json);
                }
            }
            catch (Exception e)
            {
                // Gonderilemedi: kayitlari KUYRUKTA BIRAK, sonraki turda
                // yeniden denenecek. Kanit atmiyoruz.
                _ardisikHata++;
                if (_ardisikHata == 1) _ilkHata = DateTime.UtcNow;
                // Her hata bir satir: hat kesikliyse satirlar birikir ama tavan
                // 200 KB; "neden ulasmadi" sorusunun cevabi tam da bu satirlar.
                Gunluk("POST basarisiz #" + _ardisikHata + " pid=" + OyunPid() + " kayit=" + adet + " kalp=" + kalpAdedi
                     + " kuyrukta=" + _kuyruk.Count + " : " + HataOzeti(e));
                return;
            }

            _kuyruk.RemoveRange(0, adet);
            _istekSayisi++;
            _kalpSayisi += kalpAdedi;
            if (_ardisikHata > 0)
            {
                Gunluk("POST toparlandi pid=" + OyunPid() + " - " + _ardisikHata + " hata, "
                     + (int)(DateTime.UtcNow - _ilkHata).TotalSeconds + " sn kesinti, simdi " + adet + " kayit gitti");
                _ardisikHata = 0;
            }
            else if (_istekSayisi == 1)
            {
                Gunluk("ilk POST tamam pid=" + OyunPid() + " kayit=" + adet + " kalp=" + kalpAdedi + (bosOlsaDa && adet == 0 ? " (nonce on-alma)" : ""));
            }
            NonceIsle(cevap);
        }

        /// <summary>WebException'dan HTTP kodu / durum; digerinden mesaj. Tek satir.</summary>
        static string HataOzeti(Exception e)
        {
            WebException w = e as WebException;
            if (w != null)
            {
                HttpWebResponse y = w.Response as HttpWebResponse;
                if (y != null) return "HTTP " + (int)y.StatusCode + " " + y.StatusDescription;
                return "ag: " + w.Status + " (" + w.Message + ")";
            }
            return e.GetType().Name + ": " + e.Message;
        }

        /// <summary>
        /// 13.09.2026 - OLCULDU: `WebClient` varsayilan zaman asimi 100 sn.
        /// Takilan tek bir POST kopru ipligini 100 sn kilitliyor, o surede
        /// kalp atisi sunucuya ulasmiyor ve mac kapisi oyuncuyu "kalp 70 sn
        /// once (imzali)" diye odadan cikariyordu (HayatBize61Tekme 12:27:58;
        /// ayni adreste 6 dk'da bir tek tek "imza GECERSIZ" = yanit kaybolup
        /// yeniden gonderilen kalp -> hat zaten kesikli). 8 sn: 5 sn'lik
        /// gonderim araligiyla en kotu bosluk ~13 sn, 20 sn pencerenin icinde.
        /// </summary>
        sealed class KisaZamanAsimliWebClient : WebClient
        {
            protected override WebRequest GetWebRequest(Uri adres)
            {
                WebRequest r = base.GetWebRequest(adres);
                if (r != null) r.Timeout = 8000;
                HttpWebRequest h = r as HttpWebRequest;
                if (h != null) h.ReadWriteTimeout = 8000;
                return r;
            }
        }

        int OyunPid()
        {
            try { return _oyun == null ? 0 : _oyun.Id; }
            catch { return 0; }
        }

        /// <summary>
        /// Sunucunun cevabindaki nonce'u paylasimli bellege yazar; ApexGuard
        /// bir sonraki kalp atisinda onu geri gonderir.
        ///
        /// ⚠ Bu bir TEKRAR SALDIRISI ONLEMI, kimlik dogrulama DEGIL. Nonce
        ///   sunucuya "bu kalp atisi taze" diyor, "istemci temiz" demiyor.
        /// </summary>
        void NonceIsle(string cevap)
        {
            if (string.IsNullOrEmpty(cevap) || _gorunum == null) return;
            try
            {
                object ham = new JavaScriptSerializer().DeserializeObject(cevap);
                Dictionary<string, object> d = ham as Dictionary<string, object>;
                if (d == null || !d.ContainsKey("nonce")) return;

                string onaltilik = Convert.ToString(d["nonce"]);
                if (string.IsNullOrEmpty(onaltilik) || onaltilik.Length < NONCE_BOY * 2) return;

                byte[] nonce = new byte[NONCE_BOY];
                for (int i = 0; i < NONCE_BOY; i++)
                    nonce[i] = Convert.ToByte(onaltilik.Substring(i * 2, 2), 16);

                int gecerlilik = 300;
                if (d.ContainsKey("gecerlilikSn"))
                    int.TryParse(Convert.ToString(d["gecerlilikSn"]), out gecerlilik);

                _gorunum.WriteArray(G_NONCE, nonce, 0, NONCE_BOY);
                _gorunum.Write(G_GECERLILIK, (uint)gecerlilik);
                // ⚠ SURUM EN SON: ApexGuard `surum > 0` gorunce nonce'u
                //   okuyor. Once surum yazilsaydi yarim nonce okuyabilirdi.
                long s = _gorunum.ReadInt64(G_SURUM);
                _gorunum.Write(G_SURUM, s + 1);
            }
            catch { }
        }
    }
}
