// =====================================================================
//  S2: SON SILAH - LAUNCHER
//  Giris noktasi + yapilandirma okuyucu.
//
//  Yapilandirma  launcher.cfg  dosyasindan gelir. O dosya DUZ METINDIR:
//  launcher hangi adresten indirdigini ve oyunu hangi parametrelerle
//  actigini gizlemez - acip okuyabilirsiniz, degistirebilirsiniz.
// =====================================================================
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace S2Launcher
{
    public class Ayarlar
    {
        public string Kaynak = "";                 // guncelleme adresi (https://...)
        // Ana adres cevap vermezse otomatik gecilecek adres. Alan adi
        // degistirirken ESKI adresi buraya yazin: eski launcher'i olan
        // oyuncular yeni yapilandirmayi eski adresten alir, yeni launcher
        // da ana adres duserse eskiye duserek asla ortada kalmaz.
        public string YedekKaynak = "";

        /// <summary>
        /// HD GRAFIK PAKETI deposu. Ayri bir Cloudflare R2 kovasi; kendi
        /// `manifest.json` + `manifest.sig` dosyasi var ve yalnizca
        /// `Game\HD.Res00` + `Game\HD.ResDt` iceriyor.
        ///
        /// NEDEN AYRI: standart kurulum 1.1 GB, HD eki 1.7 GB. Tek depoda
        /// olsalardi HD istemeyen oyuncu da listeyi tasimak zorunda kalirdi;
        /// ayrica iki paket birbirinin dosyasini silmeye calisirdi.
        /// Bos birakilirsa launcher'da HD secenegi hic gorunmez.
        /// </summary>
        public string HdKaynak = "";
        public string HdYedekKaynak = "";

        /// <summary>
        /// INGILIZCE ARAYUZ PAKETI deposu (`en_kaynak`). ~38 MB; arayuz
        /// dokulari + metin tablosu.
        ///
        /// HD'den farkli olarak AYRI KOVA GEREKMIYOR: guncelleyici icin
        /// "kaynak" sadece bir adres onekidir, `<kaynak>/manifest.json`,
        /// `<kaynak>/manifest.sig` ve `<kaynak>/objects/&lt;sha256&gt;` okur.
        /// Ayni kovanin altindaki bir klasor de olabilir - ornegin
        ///     en_kaynak = https://gamefiles.mdcreative.tr/en
        /// HD'nin ayri kova olmasinin sebebi boyuttu (1.7 GB), burada o
        /// gerekce yok.
        ///
        /// Bos birakilirsa launcher'da secenek hic gorunmez.
        /// </summary>
        public string EnKaynak = "";
        public string EnYedekKaynak = "";
        /// <summary>
        /// COKME RAPORU BILET UCU. Bos ya da yoksa tani TAMAMEN KAPALI -
        /// tek bayt gonderilmez, paket bile uretilmez.
        ///
        /// Burada bir anahtar YOK ve olamaz: launcher once bu adresten 10
        /// dakikalik, tek nesneye ve tek boyuta bagli imzali bir bilet
        /// alir, paketi ancak sonra yukler. Ayrinti `Tani.cs` basinda.
        /// </summary>
        public string Tani = "";

        /// <summary>
        /// ANTI-HILE RAPOR UCU. Bos ya da yoksa kopru HIC kurulmaz -
        /// paylasimli bellek bile acilmaz, tek bayt gonderilmez.
        ///
        /// ApexGuard bulgularini oyun surecinde paylasimli bellege yaziyor;
        /// launcher onlari okuyup buraya POST ediyor. Oyun surecinde ag/disk
        /// isi YOK - gerekce `ApexKanal.cs` basinda.
        ///
        /// ⚠ Buradan gelen veri SUPHE, kanit degil: makine oyuncunun,
        ///   paylasimli bellege sahte kayit yazabilir. Kesin kanit sunucunun
        ///   kendi gozcusunden gelir.
        /// </summary>
        public string Apex = "";

        /// <summary>
        /// Oyuncunun kapatma anahtari - `tani_gonder` ile ayni desen.
        /// ⚠ Kapatmak RAPORU susturur, ANTI-HILEYI DURDURMAZ: ApexGuard yine
        ///   calisir ve ihlalde oyunu kapatir. Sunucu yalnizca gormez.
        /// </summary>
        public bool ApexGonder = true;

        /// <summary>
        /// Oyuncunun kapatma anahtari. `launcher-ozel.cfg` icine
        /// `tani_gonder = 0` yazmak yeter; guncelleme o dosyaya dokunmaz.
        /// </summary>
        public bool TaniGonder = true;

        /// <summary>
        /// OYUNUN KENDI HATA AYIKLAMA GUNLUGU (`ClientLog.log`).
        /// ⛔ VARSAYILAN KAPALI - olculdu, oyunu takliyor.
        /// Gerekce `OyunArgumanlari` icinde.
        /// </summary>
        public bool OyunGunlugu = false;

        /// <summary>
        /// Her cikista rapor uret - YALNIZ SINAMA ICIN. Normalde rapor
        /// sadece anormal bitiste uretilir (dokum belirdi ya da cikis kodu
        /// sifir degil).
        /// </summary>
        public bool TaniHep = false;

        public string OyunKlasoru = ".";           // launcher.exe'ye gore
        public string Exe = "TheRaw.exe";
        public string Ip = "127.0.0.1";
        public int Port = 12000;
        public string Baslik = "D187";
        public bool Pencereli = false;
        public int Genislik = 1920;
        public int Yukseklik = 1080;
        public string Ek = "";

        /// <summary>Oyuncu portali - Discord eslestirme ve varlik durumu buradan sorulur.</summary>
        public string Site = "https://s2rebirth.com";

        /// <summary>
        /// DISCORD RICH PRESENCE (DiscordVarlik.cs). Discord Developer Portal'daki
        /// uygulamanin Application ID'si. Bos ise ozellik launcher'da HIC
        /// gorunmez. Asagidaki uc anahtar oyuncuya ait, `launcher-ozel.cfg`de durur.
        /// </summary>
        public string DiscordUygulama = "";
        public bool Discord = false;
        public string DiscordJeton = "";
        public string DiscordKullanici = "";
        public Dictionary<string, string> Baglantilar = new Dictionary<string, string>();

        /// <summary>launcher.cfg: her satir  anahtar = deger. # ile yorum.</summary>
        public static Ayarlar Oku(string yol)
        {
            var a = new Ayarlar();
            a.Uygula(yol);
            return a;
        }

        /// <summary>
        /// Bir cfg dosyasini MEVCUT ayarlarin uzerine uygular.
        /// Boylece `launcher-ozel.cfg` resmi `launcher.cfg`'yi ezebiliyor:
        /// oyuncu kendi ayarini yazar, guncelleme resmi dosyayi
        /// degistirse bile ozel dosya en son uygulandigi icin ayakta kalir.
        /// Yalnizca yazdigi anahtarlari ezer, digerleri resmi dosyadan gelir.
        /// </summary>
        public void Uygula(string yol)
        {
            var a = this;
            if (!File.Exists(yol)) return;

            foreach (string ham in File.ReadAllLines(yol, Encoding.UTF8))
            {
                string satir = ham.Trim();
                if (satir.Length == 0 || satir.StartsWith("#")) continue;
                int e = satir.IndexOf('=');
                if (e < 0) continue;
                string k = satir.Substring(0, e).Trim().ToLowerInvariant();
                string d = satir.Substring(e + 1).Trim();

                switch (k)
                {
                    case "kaynak": a.Kaynak = d; break;
                    case "yedek_kaynak": a.YedekKaynak = d; break;
                    case "hd_kaynak": a.HdKaynak = d; break;
                    case "hd_yedek_kaynak": a.HdYedekKaynak = d; break;
                    case "en_kaynak": a.EnKaynak = d; break;
                    case "en_yedek_kaynak": a.EnYedekKaynak = d; break;
                    case "tani": a.Tani = d; break;
                    case "apex": a.Apex = d; break;
                    case "apex_gonder": a.ApexGonder = !(d == "0" || d.ToLowerInvariant() == "hayir"); break;
                    case "tani_gonder": a.TaniGonder = !(d == "0" || d.ToLowerInvariant() == "hayir"); break;
                    case "oyun_gunlugu": a.OyunGunlugu = (d == "1" || d.ToLowerInvariant() == "evet"); break;
                    case "tani_hep": a.TaniHep = (d == "1" || d.ToLowerInvariant() == "evet"); break;
                    case "oyunklasoru": a.OyunKlasoru = d; break;
                    case "exe": a.Exe = d; break;
                    case "ip": a.Ip = d; break;
                    case "port": int.TryParse(d, out a.Port); break;
                    case "baslik": a.Baslik = d; break;
                    case "pencereli": a.Pencereli = (d == "1" || d.ToLowerInvariant() == "evet"); break;
                    case "genislik": int.TryParse(d, out a.Genislik); break;
                    case "yukseklik": int.TryParse(d, out a.Yukseklik); break;
                    case "ek": a.Ek = d; break;
                    case "site": a.Site = d; break;
                    case "discord_uygulama": a.DiscordUygulama = d; break;
                    case "discord": a.Discord = (d == "1" || d.ToLowerInvariant() == "evet"); break;
                    case "discord_jeton": a.DiscordJeton = d; break;
                    case "discord_kullanici": a.DiscordKullanici = d; break;
                    default:
                        // baglanti.forum = https://...
                        if (k.StartsWith("baglanti."))
                            a.Baglantilar[k.Substring(9).ToUpperInvariant()] = d;
                        break;
                }
            }
        }

        /// <summary>Oyunu acan komut satiri. THERAW-BASLATICI.ps1 ile birebir ayni.</summary>
        public string[] Argumanlar()
        {
            var arg = new List<string> {
                "-arch", "game",
                "-windowtitle", "\"" + Baslik + "\"",
                "+gs_ip", Ip,
                "+gs_port", Port.ToString()
            };
            if (Pencereli)
            {
                arg.Add("+windowed"); arg.Add("1");
                arg.Add("+ScreenWidth"); arg.Add(Genislik.ToString());
                arg.Add("+ScreenHeight"); arg.Add(Yukseklik.ToString());
            }
            // ---- OYUNUN KENDI GUNLUGU -----------------------------------
            //
            // `ShowLog` cvar'i 1 iken oyun `ClientLog.log` yaziyor; icinde
            // lobi VE dedicated trafigi paket adlariyla duruyor. ErrorCode
            // 02/03 cokme olmadigi icin dokum uretmiyor - o iki hatanin tek
            // izi bu gunluk. Bu yuzden ozellik KALDIRILMADI, ayrildi.
            //
            // ⛔ 27.08.2026: VARSAYILAN KAPALIYA CEKILDI, TANIDAN AYRILDI.
            //
            // Eskiden tani acikken gunluk de aciliyordu (tek anahtar).
            // Oyuncularin "karakterler isinlaniyor, akicilik gidiyor"
            // sikayeti arastirilirken gunlugun MALIYETI olculdu:
            //
            //     ClientLog.log      2706 satir / 129 sn
            //     nInterpolation     2,5 ms arayla -> ~400 satir/sn
            //
            // Ve gunluk fonksiyonu (`GameClient.dll` sub_10056E70) satir
            // basina: `clock()` + UC ayri `fprintf` + 2000 baytlik
            // `_vsnprintf`. Yani ~400 satir/sn = **~1200 fprintf/sn**,
            // OYUNUN KENDI IS PARCACIGINDA. Tampon dolunca diske iniyor;
            // yavas ya da mesgul diskte bu on milisaniyelik donmalar
            // uretir - tarif edilen belirtinin ta kendisi.
            //
            // ⛔ 28.08.2026 - YUKARIDAKI MEKANIZMA OLCULDU VE CURUDU.
            //
            // Gunluk yolu (`clock()` + UC `fprintf`, dosya "wtc" ile acik)
            // GERCEK MSVCR100 uzerinden birebir kosuldu:
            //
            //     satir basina  ort 1,8 us   p50 0,9 us   p99 7,5 us
            //     "wtc" (commit) ile "wt" arasinda FARK YOK:
            //         >=2 ms suren satir: 120.000'de 2  (kontrolde de ayni)
            //
            // Yani olculen 150-400 satir/sn'de maliyet CPU'nun %0,1'inden az.
            // "1200 fprintf/sn diski tikiyor" tezi YANLIS - tampon 4 KB,
            // saniyede ~24 fiziksel yazma, hicbiri bloklamiyor.
            //
            // TAKILMANIN GERCEK SEBEBI BASKAYDI: launcher'in `AgIzi`
            // ornekleyicisi (250 ms'de bir `Process.Refresh()` +
            // `WorkingSet64`/`Threads.Count`). Gerekce ve olcum `AgIzi.cs`
            // basliginda. Bu anahtar (gunluk) o arizanin sebebi DEGILDI.
            //
            // ErrorCode 02/03 arastirmasi gerektiginde O OYUNCUYA
            // `launcher-ozel.cfg` icine `oyun_gunlugu = 1` yazdirilir.
            // Tani paketi (cokme raporu + ag izi) HALA calisiyor - o
            // ayri ve hafif (250 ms'de bir, ayri surecte).
            //
            // `settings.cfg`e yazmak ISE YARAMIYOR: oyun cikarken o dosyayi
            // yeniden yaziyor ve bilmedigi satiri DUSURUYOR (olculdu).
            if (OyunGunlugu)
            {
                arg.Add("+ShowLog"); arg.Add("1");
            }
            if (!string.IsNullOrEmpty(Ek.Trim()))
                foreach (string p in Ek.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries))
                    arg.Add(p);
            return arg.ToArray();
        }
    }

    static class Program
    {
        public static string KendiKlasoru()
        {
            return Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        }

        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Guncelleyici.ArtiklariTemizle();   // onceki kendini-guncellemenin artigi

            string kok = KendiKlasoru();
            var ayar = Ayarlar.Oku(Path.Combine(kok, "launcher.cfg"));
            // Oyuncunun kendi ayari - varsa resmi dosyanin USTUNE biner.
            // Bu dosya yayinda YOK, dolayisiyla guncelleme ona hic dokunmaz.
            ayar.Uygula(Path.Combine(kok, "launcher-ozel.cfg"));
            string oyun = Path.GetFullPath(Path.Combine(kok, ayar.OyunKlasoru));

            // Arayuz dili, PENCERE ACILMADAN once belirlensin - asagidaki
            // uyari da dahil her yazi dogru dilde ciksin.
            AnaPencere.DiliOku(oyun);

            // ---- SANAL KUTU (Sandboxie) - 12.09.2026 -----------------------
            // Kutu icinde acilan launcher oyunu da kutuda acar: tek-ornek
            // kilidi ve anti-hile koprusu kutu icinde kalir, coklu istemci
            // mumkun olur (gerekce KumHavuzu.cs). Daha oyunu acmadan dur.
            string kutu = KumHavuzu.Tespit();
            if (kutu != null)
            {
                MessageBox.Show(
                    AnaPencere.S(
                        "Oyun bir sanal kutu (Sandboxie) içinde çalıştırılamaz.\n\n" +
                        "Launcher'ı doğrudan, kutu dışında başlatın.\n\n" + kutu,
                        "The game cannot run inside a sandbox (Sandboxie).\n\n" +
                        "Start the launcher directly, outside the sandbox.\n\n" + kutu),
                    "S2 Launcher", MessageBoxButtons.OK, MessageBoxIcon.Stop);
                return;
            }

            if (string.IsNullOrEmpty(ayar.Kaynak))
            {
                MessageBox.Show(
                    AnaPencere.S(
                        "launcher.cfg içinde 'kaynak' adresi tanımlı değil.\n\n" +
                        "Dosyayı bir metin düzenleyiciyle açıp güncelleme adresini yazın.",
                        "No 'kaynak' address is defined in launcher.cfg.\n\n" +
                        "Open the file in a text editor and enter the update address."),
                    "S2 Launcher", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // "S2Launcher.exe --butunluk" ile acilirsa onbellek yok sayilir ve
            // her dosya bastan hashlenir. Arayuzdeki dugmeyle ayni sey.
            bool tamDenetim = false;
            if (args != null)
                foreach (string a in args)
                    if (string.Equals(a, "--butunluk", StringComparison.OrdinalIgnoreCase))
                        tamDenetim = true;

            // Onceki seanstan kalan cokme raporu var mi? Makine kapandiysa,
            // ag yoksa ya da launcher'in kendisi olduyse paket diskte
            // bekliyor olabilir. Arka planda, sessizce - basarisiz olursa
            // paket yerinde kalir ve bir dahaki aciliste yeniden denenir.
            new System.Threading.Thread(delegate ()
            {
                try { Tani.ArtiklariGonder(oyun, ayar); } catch { }
            })
            { IsBackground = true }.Start();

            Application.Run(new AnaPencere(ayar, oyun, tamDenetim));
        }
    }
}
