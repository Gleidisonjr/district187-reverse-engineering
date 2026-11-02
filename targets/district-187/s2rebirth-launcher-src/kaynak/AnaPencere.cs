// =====================================================================
//  ANA PENCERE - launcher arayuzu.
//
//  Bu arayuz TAMAMEN elle ciziliyor: tek bir WinForms dugmesi/etiketi yok.
//  Sebep, tasarimin hazir gorsellerden olusmasi (egik dugmeler, yirtik
//  cerceveler, kan sicramalari). Onlari standart denetimlere giydirmeye
//  calismak hem cirkin hem kirilgan olurdu.
//
//  OLCU SISTEMI
//  Her sey 1280x800'luk TASARIM uzayinda yazilir (asagidaki sabitler
//  tasarim dosyasindan piksel piksel olculdu). Ekran kucukse tek bir
//  olcek carpani (_o) uygulanir; cizim de fare de ayni carpani kullanir,
//  dolayisiyla yerlesim hicbir cozunurlukte bozulmaz.
//
//  Calistirdigi TEK harici program: launcher.cfg'de 'exe' olarak yazan
//  dosya (varsayilan TheRaw.exe), yine cfg'deki parametrelerle.
// =====================================================================
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace S2Launcher
{
    public class AnaPencere : Form
    {
        // ---- TASARIM OLCULERI (launcher-tam-hali.png'den olculdu) -------
        const int TW = 1280, TH = 800;

        static readonly Rectangle R_LOGO    = new Rectangle(410,   0, 460, 340);
        static readonly Rectangle R_DISCORD = new Rectangle( 70,  40, 240,  56);
        static readonly Rectangle R_BEYAN   = new Rectangle(880,  40, 240,  56);
        static readonly Rectangle R_KUCULT  = new Rectangle(1178, 68,  30,  30);
        static readonly Rectangle R_KAPAT   = new Rectangle(1216, 68,  30,  30);
        static readonly Rectangle R_AYAR    = new Rectangle(1140, 68,  30,  30);

        // ---- AYARLAR PENCERESI (tasarim uzayi) ---------------------------
        // settings_panel.png 560x640, ekranin ortasinda.
        static readonly Rectangle R_AYAR_PANEL = new Rectangle(360, 80, 560, 640);
        const int AYAR_BASLIK_H = 60;      // panel gorselinin ust serit yuksekligi
        const int AYAR_ETIKET_SAG = 180;   // etiketler panelin solundan +180'de biter
        const int AYAR_GIRIS_X = 195;      // metin kutusu panelin solundan +195
        const int AYAR_GIRIS_W = 320;      // settings_input.png genisligi
        const int AYAR_GIRIS_H = 36;
        const int AYAR_ILK_Y = 82;         // ilk satirin panel icindeki y'si
        const int AYAR_ADIM = 44;          // satir araligi
        static readonly Rectangle R_CERCEVE = new Rectangle(110, 310, 640, 330);
        static readonly Rectangle R_GORSEL  = new Rectangle(133, 333, 594, 284); // cercevenin ic boslugu
        static readonly Rectangle R_HABER   = new Rectangle(800, 280, 400, 470);
        static readonly Rectangle R_CUBUK   = new Rectangle(130, 706, 480,  26);
        static readonly Rectangle R_DOLGU   = new Rectangle(134, 710, 472,  18);
        static readonly Rectangle R_BASLA   = new Rectangle(518, 598, 280, 140);

        const int MERMI_X = 134, MERMI_Y = 672, MERMI_W = 12, MERMI_H = 27,
                  MERMI_ARA = 15, MERMI_SAYI = 6;
        const int DURUM_X = 131, DURUM_Y = 648;
        const int ALT_Y = 736, DOSYA_X = 131, SURUM_X = 447;
        const int KUCUK_Y = 764;

        // Haber satirlari. Yildiz, "Son İstihbaratlar" basligi ve ayrac
        // cizgileri news_panel.png'nin ICINE cizilmis - onlari BURADA
        // tekrar cizmiyoruz (bir kez cizildi, ust uste binip okunmaz oldu).
        // Panelin kendi ayraclari panel-ici y=81'den baslayip 63 piksel
        // araliklarla gidiyor; satir metinleri ona hizali.
        const int H_SOL = 826, H_SAG = 1174;
        const int H_SATIR_Y = 374, H_SATIR_ARA = 63, H_SATIR_SAYI = 6;

        // ---- renkler (tasarimdan orneklendi) ----------------------------
        static readonly Color Turuncu = Color.FromArgb(228, 121,  27);
        static readonly Color Acik    = Color.FromArgb(239, 233, 224);
        static readonly Color Gri     = Color.FromArgb(140, 134, 127);
        static readonly Color TarihR  = Color.FromArgb(197, 190, 182);
        static readonly Color Kirmizi = Color.FromArgb(226,  74,  60);

        // readonly DEGIL: ayarlar penceresi kaydettikten sonra ve sifirdan
        // kurulumdan sonra yeniden okunup buraya konuyor.
        Ayarlar _ayar;
        readonly string _oyunKlasoru;
        float _o = 1f;                       // tasarim -> ekran olcegi

        readonly Dictionary<string, Image> _gorseller =
            new Dictionary<string, Image>(StringComparer.OrdinalIgnoreCase);
        readonly List<Image> _sliderler = new List<Image>();
        int _sliderSira;
        System.Windows.Forms.Timer _sliderSaat;

        // ---- durum -------------------------------------------------------
        string _durum = S("Başlatılıyor...", "Starting...");
        string _dosyaAdi = "";
        string _surumMetni = "";
        float _ilerleme;
        bool _hazir;
        bool _hata;
        List<string[]> _haberler = new List<string[]>();

        volatile bool _mesgul;
        volatile bool _tamDenetim;
        readonly bool _acilistaTamDenetim;

        class Bolge
        {
            public Rectangle R;               // tasarim uzayinda
            public string Normal, Uzerinde;   // gorsel adlari (null = cizim yok)
            public Action Tikla;
            public Func<bool> Etkin;          // null = her zaman etkin
        }
        readonly List<Bolge> _bolgeler = new List<Bolge>();
        Bolge _hedef;

        // Alt satirdaki uc kucuk yazi baglantisi. Indisle degil DOGRUDAN
        // tutuluyor: eskiden `_bolgeler[Count-2]` yaziliyordu ve listeye yeni
        // bir dugme eklenince cizim yanlis bolgeyi vurguluyordu.
        Bolge _bPencereli, _bDenetim, _bHd, _bEn, _bDiscord, _bDiscordBagla, _bDiscordIkon;

        // ---- HD GRAFIK PAKETI -------------------------------------------
        /// <summary>Oyuncunun secimi. `.launcher\paket.json` icinde yasar.</summary>
        bool _hdSecili;
        bool _enSecili;

        // =================================================================
        //  ARAYUZ DILI
        //
        //  Ingilizce paket seciliyken launcher'in KENDI yazilari da
        //  ingilizce olur - dugmeler, durum satiri, uyari pencereleri ve
        //  proje beyani dahil. Ayri bir dil dosyasi YOK: her metin ciftiyle
        //  birlikte kodun icinde duruyor, boylece yeni bir yazi eklerken
        //  cevirisini unutmak imkansiz (derleyici iki arguman istiyor) ve
        //  dagitilacak fazladan dosya olusmuyor.
        //
        //  `_ing` STATIK: `S()` de statik olmak zorunda, cunku `BEYAN`
        //  gibi statik alanlardan da cagriliyor.
        // =================================================================
        static bool _ing;

        /// <summary>Iki dilli metin. Ingilizce paket seciliyse `en`, degilse `tr`.</summary>
        internal static string S(string tr, string en) { return _ing ? en : tr; }

        /// <summary>
        /// Arayuz dilini `.launcher\paket.json`'dan okur.
        ///
        /// STATIK VE AYRI: `Program.Main` bunu pencere acilmadan ONCE
        /// cagiriyor. Yoksa "launcher.cfg icinde kaynak adresi yok" gibi
        /// acilis uyarilari her zaman Turkce cikardi - oysa o uyariyi goren
        /// oyuncu ingilizce paketi secmis olabilir.
        /// </summary>
        internal static void DiliOku(string oyunKlasoru)
        {
            try
            {
                string y = Path.Combine(Path.Combine(oyunKlasoru, ".launcher"), "paket.json");
                _ing = File.Exists(y)
                    && File.ReadAllText(y).IndexOf("\"dil\": \"en\"", StringComparison.OrdinalIgnoreCase) >= 0;
            }
            catch { _ing = false; }
        }

        /// <summary>Ingilizce dil paketinin UZERINE yazdigi tek dosya.</summary>
        const string DIL_DOSYASI = "Game/StringDatabase/Turkey/TheRaw.Strdb00p";
        /// <summary>HD deposu tanimli mi (launcher.cfg -> hd_kaynak).</summary>
        bool HdVar { get { return !string.IsNullOrEmpty(_ayar.HdKaynak); } }

        /// <summary>Ingilizce paket deposu tanimli mi (launcher.cfg -> en_kaynak).</summary>
        bool EnVar { get { return !string.IsNullOrEmpty(_ayar.EnKaynak); } }

        // ---- AYARLAR PENCERESI -------------------------------------------
        bool _ayarAcik;
        bool _ayarKapatUzerinde, _ayarKaydetUzerinde, _ayarKurUzerinde;
        readonly List<TextBox> _ayarKutulari = new List<TextBox>();
        /// <summary>Resmi `launcher.cfg` (ozel dosya UYGULANMADAN). Kaydederken
        /// karsilastirma tabani: yalnizca bundan FARKLI olan anahtar yazilir.</summary>
        Ayarlar _resmiAyar;

        /// <summary>Ayarlar penceresindeki alanlar: cfg anahtari + etiket.</summary>
        static readonly string[][] AYAR_ALANLARI = {
            new[] { "exe",              "exe" },
            new[] { "ip",               "ip" },
            new[] { "port",             "port" },
            new[] { "baslik",           "baslik" },
            new[] { "pencereli",        "pencereli" },
            new[] { "genislik",         "genislik" },
            new[] { "yukseklik",        "yukseklik" },
            new[] { "kaynak",           "kaynak" },
            new[] { "yedek_kaynak",     "yedek_kaynak" },
            new[] { "baglanti.DISCORD", "baglanti.DISCORD" },
        };

        Point _tutus;
        bool _tasiniyor;

        // ---- PROJE BEYANI penceresi --------------------------------------
        static readonly Rectangle R_BEYAN_PANEL = new Rectangle(240, 50, 826, 710);
        const int BEYAN_BASLIK_H = 66;          // ust serit yuksekligi
        const int BEYAN_KENAR = 28;             // ic bosluk
        const int BEYAN_KAYDIRMA_W = 12;        // kaydirma cubugu genisligi
        bool _beyanAcik;
        float _beyanKaydir;                     // piksel cinsinden kaydirma
        int _beyanToplam;                       // icerigin toplam yuksekligi
        bool _beyanKapatUzerinde;
        bool _beyanSurukleniyor;
        int _beyanSuruklemeBasi;
        float _beyanKaydirBasi;

        /// <summary>
        /// Beyan metni. Satir basindaki "#" o satirin BASLIK oldugunu soyler.
        /// Bos satir paragraf araligi birakir. Metni degistirmek icin burayi
        /// duzenleyip derle.cmd calistirmak yeterli.
        ///
        /// IKI DIZI, `S()` DEGIL: bu bir STATIK ALAN ve statik alanlar tip
        /// ilk kullanildiginda, yani `_ing` daha okunmadan once kuruluyor.
        /// `S()` kullanilsaydi beyan her zaman Turkce cikardi. `BEYAN`
        /// ozelligi cagri aninda dogru diziyi veriyor.
        /// </summary>
        static string[] BEYAN { get { return _ing ? BEYAN_EN : BEYAN_TR; } }

        static readonly string[] BEYAN_EN = {
            "# Nature of the Project",
            "This project is a personal, non-profit work that I develop in my spare time purely out of hobby, technical curiosity and nostalgia. At no stage has it had a commercial purpose, it does not have one now, and it will not have one in the future.",
            "",
            "# No Financial Expectation",
            "I expect no financial gain, income or benefit from this project. All costs, including server and infrastructure expenses, are covered by me personally and of my own free will.",
            "",
            "# Donations Are Not Accepted",
            "I do not accept donations in any form, through any channel.",
            "Bank transfers, crypto wallets, payment apps, digital codes, gift cards or any other means of transferring money or value are not accepted and will be returned.",
            "Anyone claiming to collect donations on my behalf is a fraud; please report them.",
            "No advantage, item or privilege is ever sold or granted inside the game. Everyone is equal.",
            "",
            "# Why I Do Not Accept Donations",
            "This is not false modesty but a deliberate choice. Money flowing into a project, even with nothing given in return:",
            "may make the project legally look like a commercial activity,",
            "may create tax obligations and the risk of an audit,",
            "may, in terms of intellectual property, destroy the project's character as a non-profit hobby work.",
            "",
            "# Transparency",
            "My Discord profile and my identity are not anonymous. Who I am is public knowledge, and precisely for that reason there is no question of my taking any of the risks listed above. This statement is valid for as long as the project exists.",
            "",
            "# Respect for Intellectual Property",
            "This project is not affiliated with, nor endorsed by, the rights holders of the original game. All rights to the related trademarks and content belong to their respective owners. Upon a valid request from the rights holders, the project will be discontinued immediately.",
            "",
            "This text is a statement of intent and of the current situation; it is the only official statement valid within the scope of the project.",
        };

        static readonly string[] BEYAN_TR = {
            S("# Projenin Niteliği", "# Nature of the Project"),
            "Bu proje; tamamen hobi, teknik merak ve nostalji amacıyla, boş zamanlarımda geliştirdiğim, kâr amacı gütmeyen kişisel bir çalışmadır. Projenin hiçbir aşamasında ticari bir amaç güdülmemiş, güdülmemektedir ve gelecekte de güdülmeyecektir.",
            "",
            "# Maddi Beklenti Yoktur",
            "Bu projeden hiçbir maddi kazanç, gelir veya menfaat beklentim yoktur. Sunucu ve altyapı maliyetleri dahil tüm giderler şahsım tarafından, kendi isteğimle karşılanmaktadır.",
            "",
            S("# Bağış Kabul Edilmemektedir", "# Donations Are Not Accepted"),
            S("Hiçbir şekilde, hiçbir kanaldan bağış kabul etmiyorum.", "I do not accept donations in any form, through any channel."),
            S("IBAN, kripto cüzdanı, Papara, dijital kod, hediye kartı veya başka herhangi bir yöntemle para ya da değer transferi kabul edilmez ve iade edilir.", "Bank transfers, crypto wallets, payment apps, digital codes, gift cards or any other means of transferring money or value are not accepted and will be returned."),
            S("Benim adıma bağış topladığını iddia eden herkes dolandırıcıdır; lütfen bildirin.", "Anyone claiming to collect donations on my behalf is a fraud; please report them."),
            S("Oyun içinde hiçbir avantaj, eşya veya ayrıcalık satılmaz ve verilmez. Herkes eşittir.", "No advantage, item or privilege is ever sold or granted inside the game. Everyone is equal."),
            "",
            S("# Neden Bağış Kabul Etmiyorum?", "# Why I Do Not Accept Donations"),
            S("Bu bir naz değil, bilinçli bir tercihtir. Karşılıksız görünse dahi bir projeye bağlı para akışı:", "This is not false modesty but a deliberate choice. Money flowing into a project, even with nothing given in return:"),
            S("Projeyi hukuken ticari faaliyet görünümüne sokabilir,", "may make the project legally look like a commercial activity,"),
            S("Vergisel yükümlülük ve inceleme riski doğurabilir,", "may create tax obligations and the risk of an audit,"),
            S("Fikri mülkiyet açısından projenin kâr amacı gütmeyen hobi çalışması niteliğini ortadan kaldırabilir.", "may, in terms of intellectual property, destroy the project's character as a non-profit hobby work."),
            "",
            S("# Şeffaflık", "# Transparency"),
            "Discord profilim ve kimliğim anonim değildir. Kim olduğum bellidir ve tam da bu nedenle yukarıda saydığım risklerin hiçbirini almam söz konusu değildir. Bu beyan, projenin var olduğu sürece geçerlidir.",
            "",
            S("# Fikri Haklara Saygı", "# Respect for Intellectual Property"),
            "Bu proje, orijinal oyunun hak sahipleriyle bağlantılı değildir ve onlar tarafından desteklenmemektedir. İlgili marka ve içeriklere ait tüm haklar, hak sahiplerine aittir. Hak sahiplerinden gelecek geçerli bir talep halinde proje derhal sonlandırılır.",
            "",
            S("Bu metin bir niyet ve durum beyanıdır; proje kapsamında geçerli tek resmî açıklamadır.", "This text is a statement of intent and of the current situation; it is the only official statement valid within the scope of the project."),
        };

        // =================================================================
        public AnaPencere(Ayarlar ayar, string oyunKlasoru, bool acilistaTamDenetim = false)
        {
            _ayar = ayar;
            _oyunKlasoru = oyunKlasoru;
            _acilistaTamDenetim = acilistaTamDenetim;
            PaketDurumOku();

            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(12, 10, 10);
            DoubleBuffered = true;
            SetStyle(ControlStyles.OptimizedDoubleBuffer
                   | ControlStyles.AllPaintingInWmPaint
                   | ControlStyles.UserPaint, true);
            Text = "S2: Son Silah";

            // Ekran 1280x800'den kucukse orantili kucult (kenarda pay birak).
            Rectangle ca = Screen.PrimaryScreen.WorkingArea;
            _o = Math.Min(1f, Math.Min((ca.Width - 40) / (float)TW,
                                       (ca.Height - 40) / (float)TH));
            if (_o < 0.5f) _o = 0.5f;
            ClientSize = new Size((int)Math.Round(TW * _o), (int)Math.Round(TH * _o));

            BolgeleriKur();

            _sliderSaat = new System.Windows.Forms.Timer { Interval = 6000 };
            _sliderSaat.Tick += delegate
            {
                if (_sliderler.Count < 2) return;
                _sliderSira = (_sliderSira + 1) % _sliderler.Count;
                Invalidate();
            };

            Shown += delegate
            {
                GorselleriYukle();
                _sliderSaat.Start();
                Invalidate();
                Baslat(_acilistaTamDenetim);
            };
        }

        void Baslat(bool tamDenetim)
        {
            if (_mesgul) return;
            _tamDenetim = tamDenetim;
            new Thread(GuncellemeAkisi) { IsBackground = true }.Start();
        }

        // -----------------------------------------------------------------
        //  GORSELLER
        // -----------------------------------------------------------------
        /// <summary>
        /// Sira ONEMLI: once varliklar-ozel\ (oyuncunun kendi gorselleri),
        /// sonra varliklar\ (resmi). "-ozel" yayina hic girmedigi icin
        /// guncelleme oraya dokunamaz.
        /// </summary>
        /// <summary>
        /// Gorseli DOSYAYI KILITLEMEDEN okur.
        ///
        /// NEDEN: `Image.FromFile` dosyayi Image'in omru boyunca acik tutuyor.
        /// Guncelleyici o dosyayi degistirmek istediginde `File.Delete` /
        /// `File.Move` IOException atardi - yani launcher KENDI arayuz
        /// gorsellerini calisirken guncelleyemiyordu. Baytlari alip bellekten
        /// kuruyoruz; dosya aninda serbest kaliyor.
        ///
        /// MemoryStream BILEREK kapatilmiyor: GDI+ akisi Image yasadigi surece
        /// okumaya devam ediyor, kapatilirsa cizimde hata verir.
        /// </summary>
        static Image GorselOku(string yol)
        {
            byte[] b = File.ReadAllBytes(yol);
            return Image.FromStream(new MemoryStream(b), false, false);
        }

        Image G(string ad)
        {
            Image i;
            if (_gorseller.TryGetValue(ad, out i)) return i;
            string kok = Program.KendiKlasoru();
            // Sira: oyuncunun kendi gorselleri -> ingilizce -> resmi -> kok.
            // `varliklar-en\` yalnizca UZERINDE YAZI OLAN dosyalari tasiyor
            // (OYUNA BASLA, PROJE BEYANI, KAYDET, haber paneli basligi);
            // gerisi resmi klasorden geliyor, yani kopya doku yok.
            string[] adaylar = _ing
                ? new string[] {
                    Path.Combine(kok, "varliklar-ozel", ad),
                    Path.Combine(kok, "varliklar-en", ad),
                    Path.Combine(kok, "varliklar", ad),
                    Path.Combine(kok, ad) }
                : new string[] {
                    Path.Combine(kok, "varliklar-ozel", ad),
                    Path.Combine(kok, "varliklar", ad),
                    Path.Combine(kok, ad) };
            foreach (string y in adaylar)
                if (File.Exists(y))
                {
                    try { i = GorselOku(y); break; } catch { }
                }
            _gorseller[ad] = i;               // null da onbelleklenir
            return i;
        }

        /// <summary>
        /// Gorselleri diskten YENIDEN okur.
        ///
        /// NEDEN GEREKLI: bos bir klasore yalnizca `S2Launcher.exe` +
        /// `launcher.cfg` atilarak kurulum yapilabiliyor - `varliklar\` de
        /// manifestten iniyor. Ama arayuz ilk cizildiginde o klasor henuz
        /// yoktu; `G()` eksik gorseli "yok" diye onbellege aldigi icin
        /// indikten sonra da gelmiyordu ve ilk acilis ciplak gorunuyordu.
        /// Guncelleme bitince onbellegi bosaltip yeniden okuyoruz.
        ///
        /// UI IS PARCACIGINDAN cagrilmali (Image nesnelerine cizim sirasinda
        /// dokunuluyor).
        /// </summary>
        void GorselleriTazele()
        {
            foreach (var c in _gorseller)
                if (c.Value != null) { try { c.Value.Dispose(); } catch { } }
            _gorseller.Clear();
            foreach (var s in _sliderler) { try { s.Dispose(); } catch { } }
            _sliderler.Clear();
            _sliderSira = 0;
            GorselleriYukle();
            Invalidate();
        }

        void GorselleriYukle()
        {
            // Slayt gorselleri istege bagli: slider1.jpg, slider2.png ...
            string[] klasorler = {
                Path.Combine(Program.KendiKlasoru(), "varliklar-ozel"),
                Path.Combine(Program.KendiKlasoru(), "varliklar")
            };
            var adlar = new List<string>();
            foreach (string k in klasorler)
            {
                if (!Directory.Exists(k)) continue;
                foreach (string y in Directory.GetFiles(k))
                {
                    string a = Path.GetFileName(y).ToLowerInvariant();
                    if (!a.StartsWith("slider")) continue;
                    if (a.StartsWith("slider_frame")) continue;      // cerceve, slayt degil
                    if (!a.EndsWith(".jpg") && !a.EndsWith(".png") && !a.EndsWith(".jpeg")) continue;
                    if (adlar.Contains(a)) continue;                 // ozel olan resmiyi ezer
                    adlar.Add(a);
                    try { _sliderler.Add(GorselOku(y)); } catch { }   // dosyayi kilitlemeden
                }
            }
        }

        // -----------------------------------------------------------------
        void BolgeleriKur()
        {
            string discord = Baglanti("DISCORD");

            _bolgeler.Add(new Bolge {
                R = R_DISCORD, Normal = "btn_discord_normal.png", Uzerinde = "btn_discord_hover.png",
                Tikla = delegate { AdresAc(discord); },
                Etkin = delegate { return !string.IsNullOrEmpty(discord); } });
            // PROJE BEYANI tarayici acmaz - metin launcher'in ICINDE gosterilir.
            // Boylece oyuncu beyani gormek icin siteye gitmek zorunda kalmaz ve
            // metin her zaman uygulamayla ayni surumde olur.
            _bolgeler.Add(new Bolge {
                R = R_BEYAN, Normal = "btn_projebeyani_normal.png", Uzerinde = "btn_projebeyani_hover.png",
                Tikla = delegate { _beyanAcik = true; _beyanKaydir = 0; Invalidate(); } });
            _bolgeler.Add(new Bolge {
                R = R_KUCULT, Normal = "btn_min_normal.png", Uzerinde = "btn_min_hover.png",
                Tikla = delegate { WindowState = FormWindowState.Minimized; } });
            _bolgeler.Add(new Bolge {
                R = R_KAPAT, Normal = "btn_close_normal.png", Uzerinde = "btn_close_hover.png",
                Tikla = delegate { Close(); } });
            _bolgeler.Add(new Bolge {
                R = R_AYAR, Normal = "gear_normal.png", Uzerinde = "gear_hover.png",
                Tikla = delegate { AyarlariAc(); },
                Etkin = delegate { return !_mesgul; } });
            _bolgeler.Add(new Bolge {
                R = R_BASLA, Normal = "btn_play_normal.png", Uzerinde = "btn_play_hover.png",
                Tikla = delegate { OyunuBaslat(); },
                Etkin = delegate { return _hazir; } });
            // Tasarimda yeri olmayan islevler: kucuk yazi baglantisi olarak.
            _bPencereli = new Bolge {
                R = new Rectangle(DOSYA_X, KUCUK_Y, 150, 18),
                // Tik ARTIK KALICI. Eskiden yalnizca bellekte degisiyordu:
                // launcher kapaninca ayar kayboluyor, oyuncu her acilista
                // yeniden tikliyordu. Simdi ayarlar penceresiyle ayni yere,
                // `launcher-ozel.cfg`ye yaziliyor.
                Tikla = delegate {
                    _ayar.Pencereli = !_ayar.Pencereli;
                    TekAyarYaz("pencereli", _ayar.Pencereli ? "1" : "0");
                    Invalidate();
                } };
            _bDenetim = new Bolge {
                R = new Rectangle(DOSYA_X + 170, KUCUK_Y, 140, 18),
                Tikla = delegate { Baslat(true); },
                Etkin = delegate { return !_mesgul; } };
            _bHd = new Bolge {
                R = new Rectangle(DOSYA_X + 330, KUCUK_Y, 170, 18),
                Tikla = delegate { HdAnahtariTiklandi(); },
                Etkin = delegate { return HdVar && !_mesgul; } };
            _bEn = new Bolge {
                R = new Rectangle(DOSYA_X + 510, KUCUK_Y, 180, 18),
                Tikla = delegate { EnAnahtariTiklandi(); },
                Etkin = delegate { return EnVar && !_mesgul; } };
            _bolgeler.Add(_bPencereli);
            _bolgeler.Add(_bDenetim);
            _bolgeler.Add(_bHd);
            _bolgeler.Add(_bEn);

            // ---- Discord Rich Presence (DiscordVarlik.cs) -------------------
            // Uygulama kimligi (launcher.cfg discord_uygulama) yoksa HIC
            // gorunmez - HD/EN ile ayni gerekce. Ayni satirin sag yarisi bos.
            //
            // 12.09.2026 (gece): kod yapistirma yerine SIMGE + tek tik.
            //   bagli degil : [simge] "Discord'a bağla"  -> giris penceresi
            //                 (oyun hesabi adi + sifre, DiscordBaglaPenceresi)
            //   bagli       : [simge] "[x] Discord'da göster · ad"  (ac/kapa)
            //                 + "Hesap değiştir"  -> ayni pencere
            // Simge `varliklar\discord_ikon_*.png` (48 px, 20 px cizilir).
            _bDiscordIkon = new Bolge {
                R = new Rectangle(DOSYA_X + 700, KUCUK_Y - 2, 20, 20),
                Normal = "discord_ikon_normal.png", Uzerinde = "discord_ikon_hover.png",
                Tikla = delegate { DiscordAnahtariTiklandi(); },
                Etkin = delegate { return DiscordVarlik.Tanimli(_ayar) && !_mesgul; } };
            _bDiscord = new Bolge {
                R = new Rectangle(DOSYA_X + 726, KUCUK_Y, 210, 18),
                Tikla = delegate { DiscordAnahtariTiklandi(); },
                Etkin = delegate { return DiscordVarlik.Tanimli(_ayar) && !_mesgul; } };
            _bDiscordBagla = new Bolge {
                R = new Rectangle(DOSYA_X + 946, KUCUK_Y, 130, 18),
                Tikla = delegate { DiscordEsleAc(); },
                Etkin = delegate { return DiscordVarlik.Tanimli(_ayar) && !_mesgul && _ayar.DiscordJeton.Trim().Length > 0; } };
            _bolgeler.Add(_bDiscordIkon);
            _bolgeler.Add(_bDiscord);
            _bolgeler.Add(_bDiscordBagla);
        }

        // =================================================================
        //  DISCORD RICH PRESENCE  (DiscordVarlik.cs)
        // =================================================================

        void DiscordAnahtariTiklandi()
        {
            if (!DiscordVarlik.Tanimli(_ayar)) return;
            if (!_ayar.Discord && _ayar.DiscordJeton.Trim().Length == 0)
            {
                // Jeton olmadan acmanin anlami yok: once eslestirme.
                DiscordEsleAc();
                return;
            }
            _ayar.Discord = !_ayar.Discord;
            TekAyarYaz("discord", _ayar.Discord ? "1" : "0");
            Invalidate();
        }

        void DiscordEsleAc()
        {
            if (!DiscordVarlik.Tanimli(_ayar) || _mesgul) return;
            using (var p = new DiscordBaglaPenceresi(_ayar))
            {
                if (p.ShowDialog(this) != DialogResult.OK) return;
                _ayar.DiscordJeton = p.Jeton;
                _ayar.DiscordKullanici = p.Kullanici;
                _ayar.Discord = true;
                TekAyarYaz("discord_jeton", p.Jeton);
                TekAyarYaz("discord_kullanici", p.Kullanici);
                TekAyarYaz("discord", "1");
                Invalidate();
            }
        }

        // =================================================================
        //  HD GRAFIK PAKETI
        //
        //  Iki paket var ve ikisi de AYNI oyun klasorune calisiyor:
        //    standart -> gamefiles...    (1.1 GB, oyunun kendisi)
        //    HD       -> gamefileshd...  (1.7 GB, sadece Game\HD.Res00+ResDt)
        //
        //  HD ekinin tek yaptigi is `Default.archcfg`'ye bir satir eklemek;
        //  oyun o arsivi de yukleyince yuksek cozunurluklu dokular
        //  arsivdekilerin yerine geciyor. Standarda donmek = iki dosyayi
        //  silmek + satiri kaldirmak. Oyunun kendisine hic dokunulmuyor.
        // =================================================================

        string PaketDurumYolu
        { get { return Path.Combine(Path.Combine(_oyunKlasoru, ".launcher"), "paket.json"); } }

        void PaketDurumOku()
        {
            _hdSecili = false;
            _enSecili = false;
            try
            {
                if (!File.Exists(PaketDurumYolu)) return;
                string s = File.ReadAllText(PaketDurumYolu);
                _hdSecili = s.IndexOf("\"paket\": \"hd\"", StringComparison.OrdinalIgnoreCase) >= 0
                         || s.IndexOf("\"hd\"", StringComparison.OrdinalIgnoreCase) >= 0;
                _enSecili = s.IndexOf("\"dil\": \"en\"", StringComparison.OrdinalIgnoreCase) >= 0;
            }
            catch { _hdSecili = false; _enSecili = false; }
            _ing = _enSecili;              // arayuz dili secimle birlikte gider
        }

        void PaketDurumYaz()
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(PaketDurumYolu));
                File.WriteAllText(PaketDurumYolu,
                    "{ \"paket\": \"" + (_hdSecili ? "hd" : "standart") + "\""
                  + ", \"dil\": \"" + (_enSecili ? "en" : "tr") + "\" }");
            }
            catch { }
        }

        void HdAnahtariTiklandi()
        {
            if (!HdVar || _mesgul) return;

            string baslik, metin;
            if (!_hdSecili)
            {
                baslik = S("HD grafik paketine geç", "Switch to the HD texture pack");
                metin =
                    S("HD grafik paketi indirilecek.\n\n", "The HD texture pack will be downloaded.\n\n")
                  + S("· İndirilecek boyut: yaklaşık 1,7 GB\n", "· Download size: about 1.7 GB\n")
                  + S("· Diskte kaplayacağı yer: yaklaşık 1,8 GB\n", "· Disk space required: about 1.8 GB\n")
                  + S("· Silah, kıyafet ve harita dokuları 2 kat çözünürlüğe çıkar\n\n", "· Weapon, outfit and map textures double in resolution\n\n")
                  + S("Oyun dosyalarınız DEĞİŞMEZ; pakete ek olarak iki dosya\n", "Your game files are NOT changed; two files are added\n")
                  + S("kurulur. İstediğiniz zaman standarda geri dönebilirsiniz.\n\n", "installed. You can go back to standard at any time.\n\n")
                  + S("Devam edilsin mi?", "Continue?");
            }
            else
            {
                baslik = S("Standart grafik paketine dön", "Back to the standard texture pack");
                metin =
                    S("HD grafik paketi kaldırılacak.\n\n", "The HD texture pack will be removed.\n\n")
                  + S("· Diskten yaklaşık 1,8 GB boşalır\n", "· About 1.8 GB of disk space is freed\n")
                  + S("· Dokular oyunun kendi çözünürlüğüne döner\n\n", "· Textures return to the game's own resolution\n\n")
                  + S("Yalnızca HD paketinin kurduğu dosyalar silinir; oyunun\n", "Only the files installed by the HD pack are deleted; the\n")
                  + S("kendisine dokunulmaz. Yeniden indirmek isterseniz aynı\n", "is left alone. If you want it again, use the same\n")
                  + S("yerden tekrar açabilirsiniz.\n\n", "switch again from the same place.\n\n")
                  + S("Devam edilsin mi?", "Continue?");
            }

            if (MessageBox.Show(this, metin, "S2 Launcher · " + baslik,
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question,
                    MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;

            _hdSecili = !_hdSecili;
            PaketDurumYaz();
            Invalidate();
            Baslat(false);          // guncelleme akisi gerisini halleder
        }

        // =================================================================
        //  INGILIZCE ARAYUZ PAKETI
        //
        //  HD ile ayni kalip: ayri depo, ayri manifest+imza, ayri defter
        //  (`kurulu-en.json`), acma/kapama. Fark tek: HD arsiv EKLIYOR
        //  (archcfg satiri), bu ise oyunun kendi dosyalarinin UZERINE yaziyor
        //  - loose dosya arsivi eziyor. O yuzden archcfg'ye dokunmuyor.
        //
        //  Kaldirinca `HepsiniKaldir()` yalnizca kendi kurduklarini siliyor;
        //  ustune yazdigi tek manifest dosyasi (metin tablosu) ise standart
        //  guncelleyici tarafindan bir sonraki acilista geri indiriliyor -
        //  cunku `Atla` listesi artik bos.
        // =================================================================

        void EnAnahtariTiklandi()
        {
            if (!EnVar || _mesgul) return;

            string baslik, metin;
            if (!_enSecili)
            {
                baslik = S("İngilizce arayüze geç", "Switch to the English interface");
                metin =
                    S("İngilizce arayüz paketi indirilecek.\n\n", "The English interface pack will be downloaded.\n\n")
                  + S("· İndirilecek boyut: yaklaşık 40 MB\n", "· Download size: about 40 MB\n")
                  + S("· Menüler, tuş listeleri, yükleme ekranları ve tüm\n", "· Menus, key lists, loading screens and all\n")
                  + S("  arayüz yazıları İngilizceye döner\n\n", "  interface text switch to English\n\n")
                  + S("Oyunun kendi arşivlerine DOKUNULMAZ; dosyalar oyun\n", "The game's own archives are NOT touched; the files are\n")
                  + S("klasörüne ek olarak kurulur. İstediğiniz zaman\n", "installed alongside the game folder. You can\n")
                  + S("Türkçeye geri dönebilirsiniz.\n\n", "switch back to Turkish at any time.\n\n")
                  + S("Devam edilsin mi?", "Continue?");
            }
            else
            {
                baslik = S("Türkçe arayüze dön", "Back to the Turkish interface");
                metin =
                    S("İngilizce arayüz paketi kaldırılacak.\n\n", "The English interface pack will be removed.\n\n")
                  + S("· Diskten yaklaşık 40 MB boşalır\n", "· About 40 MB of disk space is freed\n")
                  + S("· Arayüz oyunun kendi Türkçesine döner\n\n", "· The interface returns to the game's own Turkish\n\n")
                  + S("Yalnızca dil paketinin kurduğu dosyalar silinir.\n\n", "Only the files installed by the language pack are deleted.\n\n")
                  + S("Devam edilsin mi?", "Continue?");
            }

            if (MessageBox.Show(this, metin, "S2 Launcher · " + baslik,
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question,
                    MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;

            _enSecili = !_enSecili;
            // Arayuz dili ANINDA donuyor - oyuncu paketin inmesini beklemeden
            // ne sectigini goruyor. Gorsel onbellegi de bosaltilmali, yoksa
            // "OYUNA BASLA" dugmesi eski dilde asili kalir.
            _ing = _enSecili;
            PaketDurumYaz();
            GorselleriTazele();
            Invalidate();
            Baslat(false);
        }

        // =================================================================
        //  AYARLAR PENCERESI
        //
        //  NEREYE YAZIYOR: `launcher-ozel.cfg`.  `launcher.cfg`'ye DEGIL.
        //
        //  Neden: resmi `launcher.cfg` guncellemeyle tazelenmeye devam
        //  etmeli - adres degisirse (R2 alan adi, yedek adres, yeni bir
        //  anahtar) herkesin onu alabilmesi lazim. Oyuncunun ayari resmi
        //  dosyanin USTUNE uygulanan ayri bir dosyada yasarsa:
        //     * guncelleme oyuncunun ayarini ASLA silemez  ("-ozel" yayina
        //       hic girmiyor, butunluk denetimi de gormuyor),
        //     * resmi dosya serbestce guncellenebilir,
        //     * varsayilana donmek = tek dosyayi silmek.
        //
        //  Ustelik YALNIZCA DEGISTIRILEN anahtar yaziliyor. Oyuncu `kaynak`
        //  satirina dokunmadiysa o satir ozel dosyaya hic girmez; boylece
        //  ileride adres degisince eski adrese CIVILENIP kalmaz.
        // =================================================================

        string OzelCfgYolu { get { return Path.Combine(_oyunKlasoru, "launcher-ozel.cfg"); } }

        string AlanDegeri(string anahtar, Ayarlar a)
        {
            switch (anahtar)
            {
                case "exe": return a.Exe;
                case "ip": return a.Ip;
                case "port": return a.Port.ToString();
                case "baslik": return a.Baslik;
                case "pencereli": return a.Pencereli ? "1" : "0";
                case "discord": return a.Discord ? "1" : "0";
                case "discord_jeton": return a.DiscordJeton;
                case "discord_kullanici": return a.DiscordKullanici;
                case "genislik": return a.Genislik.ToString();
                case "yukseklik": return a.Yukseklik.ToString();
                case "kaynak": return a.Kaynak;
                case "yedek_kaynak": return a.YedekKaynak;
                default:
                    if (anahtar.StartsWith("baglanti."))
                    {
                        string d;
                        return a.Baglantilar.TryGetValue(
                            anahtar.Substring(9).ToUpperInvariant(), out d) ? d : "";
                    }
                    return "";
            }
        }

        /// <summary>
        /// `launcher-ozel.cfg` icinde TEK anahtari gunceller; dosyanin geri
        /// kalanina ve yorumlarina dokunmaz. Resmi degerle ayni olursa satir
        /// dosyadan CIKARILIR (bkz. AyarlariKaydet'teki gerekce).
        /// </summary>
        void TekAyarYaz(string anahtar, string deger)
        {
            try
            {
                string resmi = AlanDegeri(anahtar, ResmiAyarOku()).Trim();
                var satirlar = new List<string>();
                if (File.Exists(OzelCfgYolu))
                    satirlar.AddRange(File.ReadAllLines(OzelCfgYolu, Encoding.UTF8));

                // ayni anahtarin eski satirlarini at
                for (int i = satirlar.Count - 1; i >= 0; i--)
                {
                    string s = satirlar[i].Trim();
                    if (s.Length == 0 || s.StartsWith("#")) continue;
                    int e = s.IndexOf('=');
                    if (e < 0) continue;
                    if (string.Equals(s.Substring(0, e).Trim(), anahtar,
                                      StringComparison.OrdinalIgnoreCase))
                        satirlar.RemoveAt(i);
                }
                if (deger.Trim() != resmi) satirlar.Add(anahtar + " = " + deger);

                bool doluMu = false;
                foreach (string s in satirlar)
                {
                    string k = s.Trim();
                    if (k.Length > 0 && !k.StartsWith("#")) { doluMu = true; break; }
                }
                if (!doluMu)
                {
                    if (File.Exists(OzelCfgYolu)) File.Delete(OzelCfgYolu);
                    return;
                }
                File.WriteAllLines(OzelCfgYolu, satirlar.ToArray(), new UTF8Encoding(false));
            }
            catch { }   // ayar yazilamadi diye launcher'i durdurmuyoruz
        }

        void AyarlariAc()
        {
            if (_mesgul) return;
            // Resmi dosyayi ozel dosya UYGULANMADAN oku - kaydederken
            // "bu deger degistirilmis mi" sorusunun tabani bu.
            _resmiAyar = ResmiAyarOku();

            if (_ayarKutulari.Count == 0)
            {
                for (int i = 0; i < AYAR_ALANLARI.Length; i++)
                {
                    var t = new TextBox
                    {
                        BorderStyle = BorderStyle.None,
                        BackColor = Color.FromArgb(26, 22, 20),
                        ForeColor = Color.FromArgb(226, 220, 212),
                        Visible = false
                    };
                    _ayarKutulari.Add(t);
                    Controls.Add(t);
                    t.BringToFront();
                }
            }
            for (int i = 0; i < AYAR_ALANLARI.Length; i++)
                _ayarKutulari[i].Text = AlanDegeri(AYAR_ALANLARI[i][0], _ayar);

            _ayarAcik = true;
            KutulariYerlestir();
            Invalidate();
        }

        void AyarlariKapat()
        {
            _ayarAcik = false;
            foreach (var t in _ayarKutulari) t.Visible = false;
            Invalidate();
        }

        /// <summary>
        /// Ozel dosya UYGULANMADAN yalniz `launcher.cfg`. Kaydederken
        /// "bu deger degistirilmis mi" karsilastirmasinin tabani.
        /// </summary>
        Ayarlar ResmiAyarOku()
        {
            return Ayarlar.Oku(Path.Combine(_oyunKlasoru, "launcher.cfg"));
        }

        /// <summary>
        /// Metin kutulari GERCEK WinForms denetimleri; arayuzun geri kalani
        /// elle cizildigi icin konumlari tasarim uzayindan olcek carpaniyla
        /// (`_o`) ekrana cevriliyor.
        /// </summary>
        void KutulariYerlestir()
        {
            for (int i = 0; i < _ayarKutulari.Count; i++)
            {
                Rectangle r = AyarGirisR(i);
                var t = _ayarKutulari[i];
                t.Font = new Font("Consolas", Math.Max(8f, 13f * _o), FontStyle.Regular);
                // Dikeyde ortala: TextBox yuksekligi yaziya gore sabit.
                int h = t.PreferredHeight;
                t.Bounds = new Rectangle(
                    (int)((r.X + 10) * _o), (int)(r.Y * _o) + (int)(r.Height * _o - h) / 2,
                    (int)((r.Width - 20) * _o), h);
                t.Visible = _ayarAcik;
                if (_ayarAcik) t.BringToFront();
            }
        }

        Rectangle AyarGirisR(int i)
        {
            return new Rectangle(
                R_AYAR_PANEL.X + AYAR_GIRIS_X,
                R_AYAR_PANEL.Y + AYAR_ILK_Y + i * AYAR_ADIM,
                AYAR_GIRIS_W, AYAR_GIRIS_H);
        }

        Rectangle AyarKapatR()
        {
            return new Rectangle(R_AYAR_PANEL.Right - 46, R_AYAR_PANEL.Y + 16, 28, 28);
        }

        Rectangle AyarKaydetR()
        {
            return new Rectangle(R_AYAR_PANEL.X + (R_AYAR_PANEL.Width - 180) / 2,
                                 R_AYAR_PANEL.Y + 540, 180, 48);
        }

        Rectangle AyarKurR()
        {
            return new Rectangle(R_AYAR_PANEL.X + 24, R_AYAR_PANEL.Y + 600, 260, 22);
        }

        /// <summary>
        /// Degistirilen anahtarlari `launcher-ozel.cfg`'ye yazar.
        /// Resmi degerle AYNI olan anahtar dosyaya hic girmez; boylece
        /// ileride resmi deger degisince oyuncu eskisine cakili kalmaz.
        /// </summary>
        void AyarlariKaydet()
        {
            var satirlar = new List<string>();
            var degisen = new List<string>();
            for (int i = 0; i < AYAR_ALANLARI.Length; i++)
            {
                string anahtar = AYAR_ALANLARI[i][0];
                string yeni = _ayarKutulari[i].Text.Trim();
                string resmi = AlanDegeri(anahtar, _resmiAyar).Trim();
                if (yeni == resmi) continue;
                satirlar.Add(anahtar + " = " + yeni);
                degisen.Add(anahtar);
            }

            try
            {
                if (satirlar.Count == 0)
                {
                    // Hicbir sey degismemis: ozel dosya varsa KALDIR ki
                    // resmi ayarlar yeniden gecerli olsun.
                    if (File.Exists(OzelCfgYolu)) File.Delete(OzelCfgYolu);
                }
                else
                {
                    var basi = new List<string> {
                        "# =====================================================================",
                        "#  KISISEL AYARLAR  -  launcher'daki AYARLAR penceresi yazdi",
                        "#",
                        "#  Bu dosya YAYINLANMAZ, guncelleme ne ezer ne siler (adinda \"-ozel\"",
                        "#  geciyor). Resmi launcher.cfg okunduktan SONRA uygulanir, yani",
                        "#  buradaki satirlar resmi olani ezer.",
                        "#",
                        "#  Yalnizca RESMI DEGERDEN FARKLI olan anahtarlar yazilir. Varsayilana",
                        "#  donmek icin bu dosyayi silmeniz yeter.",
                        "# =====================================================================",
                        "",
                    };
                    basi.AddRange(satirlar);
                    File.WriteAllLines(OzelCfgYolu, basi.ToArray(), new UTF8Encoding(false));
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, S("Ayarlar kaydedilemedi:\n", "Settings could not be saved:\n") + ex.Message,
                    S("S2 Launcher · Ayarlar", "S2 Launcher · Settings"), MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // Bellekteki ayari da tazele: resmi + ozel, sirasiyla.
            var a = ResmiAyarOku();
            a.Uygula(OzelCfgYolu);
            _ayar = a;

            AyarlariKapat();
            MessageBox.Show(this,
                satirlar.Count == 0
                    ? S("Tüm ayarlar varsayılana döndü.\nlauncher-ozel.cfg kaldırıldı.", "All settings restored to defaults.\nlauncher-ozel.cfg removed.")
                    : degisen.Count + S(" ayar kaydedildi:\n  ", " setting(s) saved:\n  ") + string.Join(", ", degisen.ToArray())
                      + S("\n\nlauncher-ozel.cfg içine yazıldı. Güncelleme bu dosyaya\n", "\n\nWritten into launcher-ozel.cfg. Updates never touch this\n")
                      + S("dokunmaz; varsayılana dönmek için silmeniz yeter.", "file; delete it to go back to the defaults."),
                S("S2 Launcher · Ayarlar", "S2 Launcher · Settings"), MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // =================================================================
        //  OYUNU YENIDEN KUR
        // =================================================================
        void YenidenKur()
        {
            if (_mesgul) return;
            if (MessageBox.Show(this,
                    S("DİKKAT — OYUN SIFIRDAN İNDİRİLECEK\n\n", "WARNING - THE GAME WILL BE DOWNLOADED FROM SCRATCH\n\n")
                  + S("Sunucudaki listedeki HER dosya yeniden indirilip üzerine\n", "EVERY file on the server list will be downloaded again and\n")
                  + S("yazılacak. Bu, normalde korunan dosyaları da kapsar:\n\n", "overwritten. This also covers the normally protected files:\n\n")
                  + S("  · settings.cfg     (çözünürlük, grafik ayarları)\n", "  · settings.cfg     (resolution, graphics settings)\n")
                  + S("  · Profile000.gdb   (tuş atamaları, nişangâh)\n", "  · Profile000.gdb   (key bindings, crosshair)\n")
                  + S("  · launcher.cfg     (launcher ayarları)\n", "  · launcher.cfg     (launcher settings)\n")
                  + "  · Default.archcfg\n\n"
                  + S("Yaklaşık 1 GB inecek ve bu ayarlarınız SIFIRLANACAK.\n", "About 1 GB will be downloaded and these settings will be RESET.\n")
                  + S("(Kendi kaydettiğiniz launcher-ozel.cfg dosyasına\n", "(Your own saved launcher-ozel.cfg file\n")
                  + S(" dokunulmaz — kişisel launcher ayarlarınız kalır.)\n\n", " is left alone - your personal launcher settings stay.)\n\n")
                  + S("Devam edilsin mi?", "Continue?"),
                    S("S2 Launcher · Oyunu yeniden kur", "S2 Launcher · Reinstall game"),
                    MessageBoxButtons.YesNo, MessageBoxIcon.Warning,
                    MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;

            if (MessageBox.Show(this,
                    S("Son onay.\n\nOyun ayarlarınız silinecek ve her dosya baştan\n", "Final confirmation.\n\nYour game settings will be deleted and every file will be\n")
                  + S("indirilecek. Emin misiniz?", "downloaded again. Are you sure?"),
                    S("S2 Launcher · Son onay", "S2 Launcher · Final confirmation"),
                    MessageBoxButtons.YesNo, MessageBoxIcon.Warning,
                    MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;

            AyarlariKapat();
            _zorlaHepsi = true;
            Baslat(true);
        }

        volatile bool _zorlaHepsi;

        /// <summary>
        /// `Default.archcfg`'yi SECIME gore yazar. Dosya artik manifestte
        /// "korunan" oldugu icin guncelleme onu ezmiyor - sahibi launcher.
        /// </summary>
        /// <summary>
        /// Diskteki HD arsiv parcalari: `Game\HD1.Res00`, `HD2.Res00`, ...
        /// Sayilarina gore siralanir. Kac parca oldugu KODA YAZILI DEGIL -
        /// diskten okunuyor, boylece parca sayisi degisince launcher'i
        /// yeniden derlemek gerekmiyor.
        /// </summary>
        List<string> HdArsivleri()
        {
            var liste = new List<string>();
            try
            {
                string gameDir = Path.Combine(_oyunKlasoru, "Game");
                if (!Directory.Exists(gameDir)) return liste;
                foreach (string y in Directory.GetFiles(gameDir, "HD*.Res00"))
                {
                    string ad = Path.GetFileNameWithoutExtension(y);
                    // Veri dosyasi da yerinde olmayan arsivi archcfg'ye YAZMA:
                    // oyun aciliste bulamayip cokerdi.
                    if (File.Exists(Path.Combine(gameDir, ad + ".ResDt")))
                        liste.Add(Path.GetFileName(y));
                }
            }
            catch { }
            liste.Sort(delegate (string a, string b)
            {
                return SayiCoz(a).CompareTo(SayiCoz(b));
            });
            return liste;
        }

        static int SayiCoz(string ad)
        {
            int n = 0; bool bulundu = false;
            foreach (char c in ad)
            {
                if (c >= '0' && c <= '9') { n = n * 10 + (c - '0'); bulundu = true; }
                else if (bulundu) break;
            }
            return bulundu ? n : 0;
        }

        void ArchcfgYaz(bool hd)
        {
            string yol = Path.Combine(_oyunKlasoru, "Default.archcfg");
            // Oyunun kendi yazimi: ters bolu CIFT. Tek bolu ile denenmedi,
            // riske girmiyoruz - retail dosya boyle.
            var sb = new StringBuilder();
            sb.Append("game\\\\Game.Res00\n");
            sb.Append("game\\\\Update_1.Res00\n");
            sb.Append("game\\\\Update_2.Res00");
            if (hd)
                foreach (string ad in HdArsivleri())
                    sb.Append("\ngame\\\\" + ad);
            string ic = sb.ToString();
            try
            {
                if (File.Exists(yol) && File.ReadAllText(yol) == ic) return;   // gereksiz yazma yok
                File.WriteAllText(yol, ic, new UTF8Encoding(false));
            }
            catch { }
        }

        string Baglanti(params string[] anahtarlar)
        {
            foreach (string a in anahtarlar)
            {
                string d;
                if (_ayar.Baglantilar.TryGetValue(a, out d) && !string.IsNullOrEmpty(d)) return d;
            }
            return "";
        }

        // -----------------------------------------------------------------
        //  CIZIM
        // -----------------------------------------------------------------
        protected override void OnPaintBackground(PaintEventArgs e) { }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.AntiAlias;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            g.ScaleTransform(_o, _o);        // bundan sonrasi TASARIM uzayi

            Ciz(g, "bg.png", 0, 0, TW, TH);

            // slayt: cercevenin ARKASINA, "cover" olarak
            if (_sliderler.Count > 0)
            {
                Image s = _sliderler[_sliderSira % _sliderler.Count];
                float o = Math.Max(R_GORSEL.Width / (float)s.Width,
                                   R_GORSEL.Height / (float)s.Height);
                float w = s.Width * o, h = s.Height * o;
                var eski = g.Clip;
                g.SetClip(R_GORSEL);
                g.DrawImage(s, R_GORSEL.X + (R_GORSEL.Width - w) / 2f,
                               R_GORSEL.Y + (R_GORSEL.Height - h) / 2f, w, h);
                g.Clip = eski;
            }
            Ciz(g, "slider_frame.png", R_CERCEVE);
            Ciz(g, "logo.png", R_LOGO);
            Ciz(g, "news_panel.png", R_HABER);

            HaberleriCiz(g);
            AltBolumuCiz(g);

            foreach (var b in _bolgeler)
            {
                if (b.Normal == null) continue;
                bool etkin = b.Etkin == null || b.Etkin();
                string ad = (_hedef == b && etkin) ? b.Uzerinde : b.Normal;
                Image im = G(ad) ?? G(b.Normal);
                if (im == null) continue;
                if (etkin) g.DrawImage(im, b.R);
                else SolgunCiz(g, im, b.R);
            }

            KucukBaglantilariCiz(g);

            if (_beyanAcik) BeyanCiz(g);
            if (_ayarAcik) AyarlarCiz(g);
        }

        // -----------------------------------------------------------------
        //  PROJE BEYANI PENCERESI
        //  Ustte kalan, kaydirilabilir metin paneli. Acikken arkadaki
        //  dugmeler calismaz (BolgeBul basta cikiyor).
        // -----------------------------------------------------------------
        Rectangle BeyanKapatR()
        {
            return new Rectangle(R_BEYAN_PANEL.Right - 62, R_BEYAN_PANEL.Y + 18, 30, 30);
        }

        Rectangle BeyanIcerikR()
        {
            return new Rectangle(
                R_BEYAN_PANEL.X + BEYAN_KENAR,
                R_BEYAN_PANEL.Y + BEYAN_BASLIK_H + 10,
                R_BEYAN_PANEL.Width - BEYAN_KENAR * 2 - BEYAN_KAYDIRMA_W - 8,
                R_BEYAN_PANEL.Height - BEYAN_BASLIK_H - 24);
        }

        void BeyanCiz(Graphics g)
        {
            // arkayi karart
            using (var perde = new SolidBrush(Color.FromArgb(190, 6, 5, 5)))
                g.FillRectangle(perde, 0, 0, TW, TH);

            // panel govdesi
            using (var b = new SolidBrush(Color.FromArgb(250, 26, 24, 23)))
                g.FillRectangle(b, R_BEYAN_PANEL);
            using (var b = new SolidBrush(Color.FromArgb(255, 18, 17, 16)))
                g.FillRectangle(b, R_BEYAN_PANEL.X, R_BEYAN_PANEL.Y, R_BEYAN_PANEL.Width, BEYAN_BASLIK_H);
            using (var p = new Pen(Color.FromArgb(70, 255, 255, 255)))
                g.DrawRectangle(p, R_BEYAN_PANEL);
            using (var p = new Pen(Color.FromArgb(45, 255, 255, 255)))
                g.DrawLine(p, R_BEYAN_PANEL.X, R_BEYAN_PANEL.Y + BEYAN_BASLIK_H,
                              R_BEYAN_PANEL.Right, R_BEYAN_PANEL.Y + BEYAN_BASLIK_H);

            using (var f = new Font("Segoe UI", 19f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var b = new SolidBrush(Turuncu))
                g.DrawString(S("PROJE BEYANI — SORUMLULUK REDDİ VE BAĞIŞ POLİTİKASI", "PROJECT STATEMENT - DISCLAIMER AND DONATION POLICY"),
                             f, b, R_BEYAN_PANEL.X + BEYAN_KENAR, R_BEYAN_PANEL.Y + 22);

            // kapat dugmesi (kirmizi daire + capraz)
            Rectangle k = BeyanKapatR();
            using (var b = new SolidBrush(_beyanKapatUzerinde
                    ? Color.FromArgb(235, 80, 66) : Color.FromArgb(198, 47, 40)))
                g.FillEllipse(b, k);
            using (var p = new Pen(Color.White, 2.6f))
            {
                g.DrawLine(p, k.X + 10, k.Y + 10, k.Right - 10, k.Bottom - 10);
                g.DrawLine(p, k.Right - 10, k.Y + 10, k.X + 10, k.Bottom - 10);
            }

            // ---- icerik ----
            Rectangle ic = BeyanIcerikR();
            var eskiKlip = g.Clip;
            g.SetClip(ic);
            float y = ic.Y - _beyanKaydir;

            using (var fb = new Font("Segoe UI", 15f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var fp = new Font("Segoe UI", 14f, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var bb = new SolidBrush(Acik))
            using (var bp = new SolidBrush(Color.FromArgb(186, 180, 172)))
            {
                foreach (string satir in BEYAN)
                {
                    if (satir.Length == 0) { y += 12; continue; }
                    bool baslik = satir[0] == '#';
                    string metin = baslik ? satir.Substring(1).Trim() : satir;
                    Font f = baslik ? fb : fp;
                    Brush br = baslik ? (Brush)bb : bp;
                    if (baslik) y += 10;
                    SizeF olcu = g.MeasureString(metin, f, ic.Width);
                    if (y + olcu.Height > ic.Y - 40 && y < ic.Bottom + 40)
                        g.DrawString(metin, f, br, new RectangleF(ic.X, y, ic.Width, olcu.Height + 2));
                    y += olcu.Height + (baslik ? 6 : 4);
                }
            }
            g.Clip = eskiKlip;
            _beyanToplam = (int)(y + _beyanKaydir - ic.Y);

            // ---- kaydirma cubugu ----
            if (_beyanToplam > ic.Height)
            {
                int cx = R_BEYAN_PANEL.Right - BEYAN_KENAR - BEYAN_KAYDIRMA_W + 6;
                using (var b = new SolidBrush(Color.FromArgb(60, 255, 255, 255)))
                    g.FillRectangle(b, cx, ic.Y, BEYAN_KAYDIRMA_W, ic.Height);
                int tutucuH = Math.Max(40, (int)(ic.Height * (ic.Height / (float)_beyanToplam)));
                int enFazla = _beyanToplam - ic.Height;
                int ty = ic.Y + (int)((ic.Height - tutucuH) * (_beyanKaydir / Math.Max(1, enFazla)));
                using (var b = new SolidBrush(Color.FromArgb(210, 150, 146, 140)))
                    g.FillRectangle(b, cx, ty, BEYAN_KAYDIRMA_W, tutucuH);
            }
        }

        // -----------------------------------------------------------------
        //  AYARLAR PENCERESI - cizim
        // -----------------------------------------------------------------
        void AyarlarCiz(Graphics g)
        {
            using (var perde = new SolidBrush(Color.FromArgb(190, 0, 0, 0)))
                g.FillRectangle(perde, 0, 0, TW, TH);

            Image panel = G("settings_panel.png");
            if (panel != null) g.DrawImage(panel, R_AYAR_PANEL);
            else
            {
                using (var b = new SolidBrush(Color.FromArgb(250, 26, 24, 23)))
                    g.FillRectangle(b, R_AYAR_PANEL);
                using (var p = new Pen(Color.FromArgb(70, 255, 255, 255)))
                    g.DrawRectangle(p, R_AYAR_PANEL);
            }

            // baslik
            Image disli = G("gear_normal.png");
            if (disli != null)
                g.DrawImage(disli, R_AYAR_PANEL.X + 22, R_AYAR_PANEL.Y + 16, 26, 26);
            using (var f = new Font("Segoe UI", 20f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var b = new SolidBrush(Acik))
                g.DrawString(S("AYARLAR", "SETTINGS"), f, b, R_AYAR_PANEL.X + 58, R_AYAR_PANEL.Y + 16);

            // kapat
            Rectangle k = AyarKapatR();
            using (var b = new SolidBrush(_ayarKapatUzerinde
                    ? Color.FromArgb(235, 80, 66) : Color.FromArgb(198, 47, 40)))
                g.FillEllipse(b, k);
            using (var p = new Pen(Color.White, 2.4f))
            {
                g.DrawLine(p, k.X + 9, k.Y + 9, k.Right - 9, k.Bottom - 9);
                g.DrawLine(p, k.Right - 9, k.Y + 9, k.X + 9, k.Bottom - 9);
            }

            // satirlar
            Image giris = G("settings_input.png");
            using (var fe = new Font("Segoe UI", 13f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var be = new SolidBrush(Turuncu))
            {
                var sagaYasli = new StringFormat { Alignment = StringAlignment.Far,
                                                   LineAlignment = StringAlignment.Center };
                for (int i = 0; i < AYAR_ALANLARI.Length; i++)
                {
                    Rectangle r = AyarGirisR(i);
                    if (giris != null) g.DrawImage(giris, r);
                    else using (var b = new SolidBrush(Color.FromArgb(255, 26, 22, 20)))
                        g.FillRectangle(b, r);
                    g.DrawString(AYAR_ALANLARI[i][1], fe, be,
                        new RectangleF(R_AYAR_PANEL.X + 20,
                                       r.Y, AYAR_ETIKET_SAG - 20, r.Height), sagaYasli);
                }
                sagaYasli.Dispose();
            }

            // KAYDET
            Rectangle kd = AyarKaydetR();
            Image kb = G(_ayarKaydetUzerinde ? "btn_kaydet_hover.png" : "btn_kaydet_normal.png");
            if (kb != null) g.DrawImage(kb, kd);
            else
            {
                using (var b = new SolidBrush(Turuncu)) g.FillRectangle(b, kd);
                using (var f = new Font("Segoe UI", 15f, FontStyle.Bold, GraphicsUnit.Pixel))
                using (var b = new SolidBrush(Color.White))
                {
                    var ortala = new StringFormat { Alignment = StringAlignment.Center,
                                                    LineAlignment = StringAlignment.Center };
                    g.DrawString(S("KAYDET", "SAVE"), f, b, kd, ortala);
                    ortala.Dispose();
                }
            }

            // OYUNU YENIDEN KUR - yikici, o yuzden kucuk ve kirmizi
            Rectangle yk = AyarKurR();
            using (var f = new Font("Segoe UI", 12f, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var b = new SolidBrush(_ayarKurUzerinde
                    ? Color.FromArgb(240, 96, 84) : Color.FromArgb(170, 74, 66)))
                g.DrawString(S("⟳  Oyunu yeniden kur (her şeyi sıfırla)", "⟳  Reinstall game (reset everything)"), f, b, yk.X, yk.Y);
        }

        void BeyanKaydir(float delta)
        {
            int gorunur = BeyanIcerikR().Height;
            int enFazla = Math.Max(0, _beyanToplam - gorunur);
            _beyanKaydir = Math.Max(0, Math.Min(enFazla, _beyanKaydir + delta));
            Invalidate();
        }

        protected override void OnMouseWheel(MouseEventArgs e)
        {
            base.OnMouseWheel(e);
            if (_beyanAcik) BeyanKaydir(-e.Delta * 0.6f);
        }

        protected override bool ProcessDialogKey(Keys keyData)
        {
            if (_ayarAcik)
            {
                if (keyData == Keys.Escape) { AyarlariKapat(); return true; }
            }
            if (_beyanAcik)
            {
                if (keyData == Keys.Escape) { _beyanAcik = false; Invalidate(); return true; }
                if (keyData == Keys.Down) { BeyanKaydir(40); return true; }
                if (keyData == Keys.Up) { BeyanKaydir(-40); return true; }
                if (keyData == Keys.PageDown) { BeyanKaydir(BeyanIcerikR().Height - 40); return true; }
                if (keyData == Keys.PageUp) { BeyanKaydir(-(BeyanIcerikR().Height - 40)); return true; }
            }
            return base.ProcessDialogKey(keyData);
        }

        void Ciz(Graphics g, string ad, Rectangle r) { Ciz(g, ad, r.X, r.Y, r.Width, r.Height); }
        void Ciz(Graphics g, string ad, int x, int y, int w, int h)
        {
            Image i = G(ad);
            if (i != null) g.DrawImage(i, x, y, w, h);
        }

        /// <summary>Etkin olmayan dugme: soluk ve yari saydam.</summary>
        static void SolgunCiz(Graphics g, Image im, Rectangle r)
        {
            var m = new ColorMatrix(new float[][] {
                new float[] {0.45f,0.45f,0.45f,0,0},
                new float[] {0.40f,0.40f,0.40f,0,0},
                new float[] {0.15f,0.15f,0.15f,0,0},
                new float[] {0,0,0,0.35f,0},
                new float[] {0,0,0,0,1}});
            using (var ia = new ImageAttributes())
            {
                ia.SetColorMatrix(m);
                g.DrawImage(im, r, 0, 0, im.Width, im.Height, GraphicsUnit.Pixel, ia);
            }
        }

        // -----------------------------------------------------------------
        void HaberleriCiz(Graphics g)
        {
            var liste = _haberler;
            if (liste.Count == 0) return;

            using (var fb = new Font("Segoe UI", 14f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var fa = new Font("Segoe UI", 13f, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var ft = new Font("Segoe UI", 12.5f, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var bb = new SolidBrush(Acik))
            using (var ba = new SolidBrush(Gri))
            using (var bt = new SolidBrush(TarihR))
            using (var sag = new StringFormat { Alignment = StringAlignment.Far })
            {
                for (int i = 0; i < H_SATIR_SAYI && i < liste.Count; i++)
                {
                    int y = H_SATIR_Y + i * H_SATIR_ARA;
                    g.DrawString(liste[i][1], fb, bb, H_SOL + 2, y);
                    if (liste[i][0].Length > 0)
                        g.DrawString(liste[i][0], ft, bt,
                            new RectangleF(H_SOL, y + 1, H_SAG - H_SOL - 2, 20), sag);
                    if (liste[i][2].Length > 0)
                        g.DrawString(liste[i][2], fa, ba, H_SOL + 2, y + 21);
                }
            }
        }

        // -----------------------------------------------------------------
        void AltBolumuCiz(Graphics g)
        {
            // Durum metni uzun olabiliyor (ozellikle hata mesajlari). BASLA
            // dugmesinin uzerine tasmasin diye genislikle sinirlandirilip
            // sonuna "..." konuyor.
            using (var f = new Font("Georgia", 17f, FontStyle.Bold | FontStyle.Italic, GraphicsUnit.Pixel))
            using (var b = new SolidBrush(_hata ? Kirmizi : Acik))
            using (var bicim = new StringFormat
            {
                Trimming = StringTrimming.EllipsisCharacter,
                FormatFlags = StringFormatFlags.NoWrap
            })
                g.DrawString(_durum, f, b,
                    new RectangleF(DURUM_X, DURUM_Y, R_BASLA.X - DURUM_X - 20, 24), bicim);

            Image mermi = G("bullet.png");
            if (mermi != null)
                for (int i = 0; i < MERMI_SAYI; i++)
                    g.DrawImage(mermi, MERMI_X + i * MERMI_ARA, MERMI_Y, MERMI_W, MERMI_H);

            Ciz(g, "progress_track.png", R_CUBUK);

            Image dolgu = G("progress_fill.png");
            float p = Math.Max(0f, Math.Min(1f, _ilerleme));
            if (dolgu != null && p > 0.001f)
            {
                int w = (int)Math.Round(R_DOLGU.Width * p);
                if (w < 2) w = 2;
                g.DrawImage(dolgu, new Rectangle(R_DOLGU.X, R_DOLGU.Y, w, R_DOLGU.Height),
                            0, 0, Math.Max(1, (int)Math.Round(dolgu.Width * p)), dolgu.Height,
                            GraphicsUnit.Pixel);
            }

            using (var f = new Font("Segoe UI", 13f, FontStyle.Regular, GraphicsUnit.Pixel))
            using (var b = new SolidBrush(Turuncu))
            {
                if (_dosyaAdi.Length > 0) g.DrawString(_dosyaAdi, f, b, DOSYA_X, ALT_Y);
                if (_surumMetni.Length > 0) g.DrawString(_surumMetni, f, b, SURUM_X, ALT_Y);
            }
        }

        void KucukBaglantilariCiz(Graphics g)
        {
            using (var f = new Font("Segoe UI", 12f, FontStyle.Regular, GraphicsUnit.Pixel))
            {
                using (var br = new SolidBrush(_hedef == _bPencereli ? Turuncu : Gri))
                    g.DrawString((_ayar.Pencereli ? "[x] " : "[  ] ") + S("Pencereli çalıştır", "Windowed mode"),
                                 f, br, _bPencereli.R.X, _bPencereli.R.Y);
                using (var br = new SolidBrush(_hedef == _bDenetim ? Turuncu : Gri))
                    g.DrawString(S("Bütünlük denetimi", "Integrity check"), f, br, _bDenetim.R.X, _bDenetim.R.Y);
                // HD deposu tanimli degilse secenegi HIC gostermiyoruz:
                // tiklanamayan soluk bir yazi "bozuk mu?" sorusu doguruyor.
                if (HdVar)
                    using (var br = new SolidBrush(_hedef == _bHd ? Turuncu : Gri))
                        g.DrawString((_hdSecili ? "[x] " : "[  ] ") + S("HD grafik paketi", "HD texture pack"),
                                     f, br, _bHd.R.X, _bHd.R.Y);
                if (EnVar)
                    using (var br = new SolidBrush(_hedef == _bEn ? Turuncu : Gri))
                        g.DrawString((_enSecili ? "[x] " : "[  ] ") + "English interface",
                                     f, br, _bEn.R.X, _bEn.R.Y);
                if (DiscordVarlik.Tanimli(_ayar))
                {
                    // Simgeyi genel dongu cizdi (_bDiscordIkon.Normal); burada yazi.
                    bool bagli = _ayar.DiscordJeton.Trim().Length > 0;
                    string yazi = bagli
                        ? (_ayar.Discord ? "[x] " : "[  ] ") + S("Discord'da göster", "Show on Discord")
                          + " · " + (_ayar.DiscordKullanici.Length > 0 ? _ayar.DiscordKullanici : "✓")
                        : S("Discord'a bağla", "Link Discord");
                    bool vurgu = _hedef == _bDiscord || _hedef == _bDiscordIkon;
                    using (var br = new SolidBrush(vurgu ? Turuncu : Gri))
                        g.DrawString(yazi, f, br, _bDiscord.R.X, _bDiscord.R.Y);
                    if (bagli)
                        using (var br = new SolidBrush(_hedef == _bDiscordBagla ? Turuncu : Gri))
                            g.DrawString(S("Hesap değiştir", "Change account"), f, br, _bDiscordBagla.R.X, _bDiscordBagla.R.Y);
                }
            }
        }

        // -----------------------------------------------------------------
        //  FARE (tasarim uzayina cevirerek)
        // -----------------------------------------------------------------
        Point Tasarima(Point p) { return new Point((int)(p.X / _o), (int)(p.Y / _o)); }

        Bolge BolgeBul(Point t)
        {
            // Ustteki pencerelerden biri acikken arkadaki dugmeler calismaz.
            if (_beyanAcik || _ayarAcik) return null;
            for (int i = _bolgeler.Count - 1; i >= 0; i--)
            {
                var b = _bolgeler[i];
                if (!b.R.Contains(t)) continue;
                if (b.Etkin != null && !b.Etkin()) continue;
                // Gorselli dugmelerde SAYDAM piksele tiklanmasin: egik dugmeler
                // ve kan sicramali BASLA dugmesi dikdortgen degil.
                if (b.Normal != null)
                {
                    var bm = G(b.Normal) as Bitmap;
                    if (bm != null)
                    {
                        int lx = (int)((t.X - b.R.X) * (bm.Width / (float)b.R.Width));
                        int ly = (int)((t.Y - b.R.Y) * (bm.Height / (float)b.R.Height));
                        if (lx >= 0 && ly >= 0 && lx < bm.Width && ly < bm.Height
                            && bm.GetPixel(lx, ly).A < 24) continue;
                    }
                }
                return b;
            }
            return null;
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);

            if (_ayarAcik)
            {
                Point ta = Tasarima(e.Location);
                bool k = AyarKapatR().Contains(ta);
                bool s = AyarKaydetR().Contains(ta);
                bool r = AyarKurR().Contains(ta);
                if (k != _ayarKapatUzerinde || s != _ayarKaydetUzerinde || r != _ayarKurUzerinde)
                {
                    _ayarKapatUzerinde = k; _ayarKaydetUzerinde = s; _ayarKurUzerinde = r;
                    Invalidate();
                }
                Cursor = (k || s || r) ? Cursors.Hand : Cursors.Default;
                return;
            }

            if (_beyanAcik)
            {
                Point t2 = Tasarima(e.Location);
                if (_beyanSurukleniyor)
                {
                    Rectangle ic = BeyanIcerikR();
                    int enFazla = Math.Max(1, _beyanToplam - ic.Height);
                    int tutucuH = Math.Max(40, (int)(ic.Height * (ic.Height / (float)Math.Max(1, _beyanToplam))));
                    float oran = enFazla / (float)Math.Max(1, ic.Height - tutucuH);
                    _beyanKaydir = Math.Max(0, Math.Min(enFazla,
                        _beyanKaydirBasi + (t2.Y - _beyanSuruklemeBasi) * oran));
                    Invalidate();
                    return;
                }
                bool ust = BeyanKapatR().Contains(t2);
                if (ust != _beyanKapatUzerinde) { _beyanKapatUzerinde = ust; Invalidate(); }
                Cursor = ust ? Cursors.Hand : Cursors.Default;
                return;
            }

            if (_tasiniyor)
            {
                Point ek = PointToScreen(e.Location);
                Location = new Point(ek.X - _tutus.X, ek.Y - _tutus.Y);
                return;
            }
            Bolge y = BolgeBul(Tasarima(e.Location));
            if (y != _hedef)
            {
                _hedef = y;
                Cursor = (y != null) ? Cursors.Hand : Cursors.Default;
                Invalidate();
            }
        }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            base.OnMouseDown(e);
            if (e.Button != MouseButtons.Left) return;

            // Ayarlar acikken pencere surukleme yok - metin kutulari
            // dogrudan kendi tiklamalarini aliyor.
            if (_ayarAcik) return;

            if (_beyanAcik)
            {
                Point t2 = Tasarima(e.Location);
                Rectangle ic = BeyanIcerikR();
                int cx = R_BEYAN_PANEL.Right - BEYAN_KENAR - BEYAN_KAYDIRMA_W + 6;
                var cubuk = new Rectangle(cx, ic.Y, BEYAN_KAYDIRMA_W, ic.Height);
                if (_beyanToplam > ic.Height && cubuk.Contains(t2))
                {
                    _beyanSurukleniyor = true;
                    _beyanSuruklemeBasi = t2.Y;
                    _beyanKaydirBasi = _beyanKaydir;
                }
                return;                       // panel acikken pencere surukleme yok
            }

            if (BolgeBul(Tasarima(e.Location)) != null) return;
            _tasiniyor = true;
            _tutus = e.Location;
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);

            if (_ayarAcik)
            {
                if (e.Button != MouseButtons.Left) return;
                Point ta = Tasarima(e.Location);
                if (AyarKapatR().Contains(ta) || !R_AYAR_PANEL.Contains(ta))
                {
                    AyarlariKapat();
                    _ayarKapatUzerinde = _ayarKaydetUzerinde = _ayarKurUzerinde = false;
                    Cursor = Cursors.Default;
                    return;
                }
                if (AyarKaydetR().Contains(ta)) { AyarlariKaydet(); return; }
                if (AyarKurR().Contains(ta)) { YenidenKur(); return; }
                return;
            }

            if (_beyanAcik)
            {
                if (_beyanSurukleniyor) { _beyanSurukleniyor = false; return; }
                if (e.Button != MouseButtons.Left) return;
                Point t2 = Tasarima(e.Location);
                // Kapat dugmesi ya da panelin DISI -> kapat.
                if (BeyanKapatR().Contains(t2) || !R_BEYAN_PANEL.Contains(t2))
                {
                    _beyanAcik = false;
                    _beyanKapatUzerinde = false;
                    Cursor = Cursors.Default;
                    Invalidate();
                }
                return;
            }

            if (_tasiniyor) { _tasiniyor = false; return; }
            if (e.Button != MouseButtons.Left) return;
            Bolge b = BolgeBul(Tasarima(e.Location));
            if (b != null && b.Tikla != null) b.Tikla();
        }

        protected override void OnMouseLeave(EventArgs e)
        {
            base.OnMouseLeave(e);
            if (_hedef != null) { _hedef = null; Cursor = Cursors.Default; Invalidate(); }
        }

        // -----------------------------------------------------------------
        //  PENCERE SIMGESI
        //  Gorev cubugu / Alt-Tab simgesi exe'nin DOSYA simgesinden gelmez;
        //  calisan pencerenin kendi simgesinden gelir. Ayarlanmazsa WinForms
        //  varsayilan .NET simgesini koyuyor.
        // -----------------------------------------------------------------
        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        static extern IntPtr LoadImage(IntPtr hinst, string ad, uint tur, int cx, int cy, uint bayrak);
        [DllImport("user32.dll")]
        static extern int GetSystemMetrics(int olcu);
        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        static extern IntPtr SendMessage(IntPtr pencere, int mesaj, IntPtr wParam, IntPtr lParam);
        [DllImport("kernel32.dll", CharSet = CharSet.Auto)]
        static extern IntPtr GetModuleHandle(string ad);

        const uint IMAGE_ICON = 1, LR_SHARED = 0x8000;
        const int SM_CXICON = 11, SM_CXSMICON = 49;
        const int WM_SETICON = 0x0080, ICON_SMALL = 0, ICON_BIG = 1;

        static IntPtr GomuluIkon(int boyut)
        {
            return LoadImage(GetModuleHandle(null), "#32512", IMAGE_ICON, boyut, boyut, LR_SHARED);
        }

        void SimgeyiKur()
        {
            try
            {
                IntPtr buyuk = GomuluIkon(GetSystemMetrics(SM_CXICON));
                IntPtr kucuk = GomuluIkon(GetSystemMetrics(SM_CXSMICON));
                if (buyuk == IntPtr.Zero && kucuk == IntPtr.Zero) return;
                if (buyuk != IntPtr.Zero)
                {
                    Icon = Icon.FromHandle(buyuk);
                    SendMessage(Handle, WM_SETICON, (IntPtr)ICON_BIG, buyuk);
                }
                if (kucuk != IntPtr.Zero)
                    SendMessage(Handle, WM_SETICON, (IntPtr)ICON_SMALL, kucuk);
            }
            catch { }
        }

        protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); SimgeyiKur(); }
        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            // WinForms `Icon`den turettigi KUCUK simgeyi sonradan tekrar
            // yaziyor; bu yuzden pencere gorundukten sonra bir kez daha.
            SimgeyiKur();
        }

        // -----------------------------------------------------------------
        //  GUNCELLEME AKISI (arka planda)
        // -----------------------------------------------------------------
        void GuncellemeAkisi()
        {
            _mesgul = true;
            bool tam = _tamDenetim;
            Yaz(delegate { _hazir = false; _hata = false; });
            try
            {
                HaberleriYukle();

                bool zorla = _zorlaHepsi;
                _zorlaHepsi = false;          // tek seferlik

                var g = new Guncelleyici(_ayar.Kaynak, _ayar.YedekKaynak,
                                         _oyunKlasoru, IlerlemeGeldi);
                g.TamDenetim = tam;
                g.ZorlaHepsi = zorla;
                if (zorla) Durum(S("Oyun sıfırdan kuruluyor - her dosya yeniden inecek...", "Reinstalling the game - every file will be downloaded again..."), 0, 1);
                // HD deposunun kurdugu dosyalar bizim manifestimizde yok;
                // "yabanci dosya" diye raporlanmasinlar.
                g.EkMuaf = HdKuruluListe();
                g.EkMuaf.AddRange(EnKuruluListe());
                // Dil paketi seciliyken metin tablosunun sahibi O; standart
                // guncelleyici dokunmasin (yoksa her aciliste Turkcesini geri
                // indirir, dil asamasi Ingilizcesini geri yazar).
                if (_enSecili && EnVar) g.Atla.Add(DIL_DOSYASI);
                if (tam) Durum(S("Bütünlük denetimi - her dosya baştan hesaplanıyor...", "Integrity check - every file is being rehashed..."), 0, 1);

                Manifest m = g.ManifestIndir();
                Yaz(delegate { _surumMetni = S("Sürüm ", "Version ") + m.Surum; });

                List<Is> isler = g.FarkiCikar(m);
                bool indirilenVar = false;
                foreach (var i in isler) if (!i.Silinecek) { indirilenVar = true; break; }
                if (isler.Count == 0)
                {
                    Durum(tam ? S("Bütünlük denetimi tamam - ", "Integrity check complete - ") + m.Dosyalar.Count + S(" dosyanın hepsi doğru.", " files are all correct.")
                              : S("Oyun güncel. Sıkı dur asker.", "Game is up to date. Stay sharp, soldier."), 1, 1);
                }
                else
                {
                    long boyut = 0; int indirilecek = 0;
                    foreach (var i in isler) if (!i.Silinecek) { boyut += i.Boyut; indirilecek++; }
                    Durum(indirilecek + S(" dosya güncellenecek (", " file(s) will be updated (") + Bicimle(boyut) + ")", 0, 1);
                    Thread.Sleep(500);
                    g.Uygula(isler, m);

                    // Launcher'in kendi exe'si YA DA launcher.cfg yenilendiyse
                    // bastan acmak zorunda: ikisinde de bellekteki durum
                    // bayatladi. cfg icin gerekcesi Guncelleyici.AyarYenilendi
                    // ustunde yazili - kisaca oyunu acan komut satiri
                    // (`+gs_ip`) acilista okunan `_ayar`dan kuruluyor ve
                    // guncellemeyi alip kapatmadan Baslat'a basan oyuncu ESKI
                    // sunucu adresine gidiyordu.
                    if (g.YenidenBaslatmaGerek)
                    {
                        Durum(g.LauncherYenilendi
                                ? S("Launcher güncellendi, yeniden başlatılıyor...", "Launcher updated, restarting...")
                                : S("Ayarlar güncellendi, yeniden başlatılıyor...", "Settings updated, restarting..."), 1, 1);
                        Thread.Sleep(800);
                        Yaz(delegate { KendiniYenidenBaslat(); });
                        return;
                    }
                    Durum(S("Güncelleme tamamlandı.", "Update complete."), 1, 1);
                }

                // Toplu silme korumasi devreye girdiyse sessiz gecmeyelim.
                if (g.TopluSilmeEngellendi > 0)
                {
                    int n = g.TopluSilmeEngellendi;
                    Yaz(delegate
                    {
                        MessageBox.Show(this,
                            S("Sunucudaki liste, kurulumunuzdaki ", "The server list says that ") + n + S(" dosyanın\n", " of your files\n")
                          + S("silinmesi gerektiğini söylüyor. Bu, listenin bozuk ya da\n", "should be deleted. That means the list is corrupt or was\n")
                          + S("yarım inmiş olabileceği anlamına gelir.\n\n", "only partly downloaded.\n\n")
                          + S("GÜVENLİK GEREĞİ HİÇBİR DOSYA SİLİNMEDİ.\n\n", "AS A SAFETY MEASURE, NO FILE WAS DELETED.\n\n")
                          + S("Oyun çalışıyorsa sorun yok. Emin olmak isterseniz\n", "If the game runs, there is no problem. To be sure, run\n")
                          + S("\"Bütünlük denetimi\" çalıştırın.", "\"Integrity check\"."),
                            S("S2 Launcher · Toplu silme engellendi", "S2 Launcher · Mass deletion blocked"),
                            MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    });
                }

                // ---- HD GRAFIK PAKETI ----------------------------------
                // Standart guncelleme bittikten SONRA calisir: HD eki
                // oyunun uzerine biniyor, once temelin dogru olmasi lazim.
                HdAsamasi();

                // ---- INGILIZCE ARAYUZ PAKETI ---------------------------
                // Standart guncellemeden SONRA: ustune yazdigi dosyalarin
                // once dogru surumde olmasi gerekiyor.
                DilAsamasi();

                // Sifirdan kurulumda launcher.cfg de yenilendi - bellekteki
                // ayari tazeleyelim (ozel dosya yine en son uygulaniyor).
                //
                // NOT (24.08.2026): normal guncellemede `launcher.cfg`
                // degistiginde buraya HIC gelinmiyor - yukarida
                // `AyarYenilendi` dalinda launcher kendini yeniden
                // baslatiyor. Bellekte tek alan tazelemek yerine bastan
                // acmak tercih edildi: `_ayar` disinda cfg'ye bagli baska
                // durum da var (kaynak adresleri, gorseller, dil secimi) ve
                // hepsini elle tazelemeye calismak eksik kalmaya aciktir.
                if (zorla)
                {
                    var taze = ResmiAyarOku();
                    taze.Uygula(OzelCfgYolu);
                    Yaz(delegate { _ayar = taze; });
                }

                // Arayuz gorselleri bu guncellemede inmis olabilir (bos
                // klasore yalnizca exe + cfg atilarak kurulum yapiliyor).
                // Onbellek "yok" degerini tuttugu icin yeniden okutuyoruz.
                if (indirilenVar) Yaz(delegate { GorselleriTazele(); });

                if (tam) DenetimRaporu(g, m, isler);
                Yaz(delegate { _hazir = true; _ilerleme = 1f; _dosyaAdi = ""; Invalidate(); });
            }
            catch (Exception ex)
            {
                string msj = ex.Message;
                Yaz(delegate
                {
                    _hata = true;
                    _durum = S("Güncelleme yapılamadı: ", "Update failed: ") + msj;
                    _dosyaAdi = "";
                    _hazir = File.Exists(Path.Combine(_oyunKlasoru, _ayar.Exe));
                    Invalidate();
                });
            }
            finally { _mesgul = false; }
        }

        /// <summary>HD deposunun kurdugu dosyalarin listesi (yoksa bos).</summary>
        List<string> HdKuruluListe()
        {
            try
            {
                var s = new Guncelleyici(_ayar.HdKaynak ?? "", _oyunKlasoru, null);
                s.Etiket = "hd";
                return s.KuruluListeOku();
            }
            catch { return new List<string>(); }
        }

        /// <summary>Dil paketinin kurdugu dosyalarin listesi (yoksa bos).</summary>
        List<string> EnKuruluListe()
        {
            try
            {
                var s = new Guncelleyici(_ayar.EnKaynak ?? "", _oyunKlasoru, null);
                s.Etiket = "en";
                return s.KuruluListeOku();
            }
            catch { return new List<string>(); }
        }

        /// <summary>
        /// Secime gore ingilizce arayuz paketini kurar ya da kaldirir.
        ///
        /// HD'den iki farki var:
        ///   * `Default.archcfg`'ye DOKUNMAZ - arsiv eklemiyor, oyunun kendi
        ///     dosyalarinin uzerine loose dosya biniyor.
        ///   * Kaldirinca metin tablosu geri gelmeli: `HepsiniKaldir()` dil
        ///     paketinin kopyasini siler, standart guncelleyici bir sonraki
        ///     acilista (artik `Atla` bos oldugu icin) Turkcesini indirir.
        ///     Oyuncu beklemesin diye burada hemen bir tur daha atiyoruz.
        ///
        /// HATA YUTULUYOR: depo cevap vermezse oyun yine de acilmali.
        /// </summary>
        void DilAsamasi()
        {
            if (!EnVar) return;
            try
            {
                var ge = new Guncelleyici(_ayar.EnKaynak, _ayar.EnYedekKaynak,
                                          _oyunKlasoru, IlerlemeGeldi);
                ge.Etiket = "en";

                if (_enSecili)
                {
                    Durum(S("İngilizce arayüz paketi denetleniyor...", "Checking English interface pack..."), 0, 1);
                    Manifest me = ge.ManifestIndir();
                    List<Is> ise = ge.FarkiCikar(me);
                    if (ise.Count > 0)
                    {
                        long boyut = 0;
                        foreach (var i in ise) if (!i.Silinecek) boyut += i.Boyut;
                        Durum(S("İngilizce arayüz indiriliyor (", "Downloading English interface (") + Bicimle(boyut) + ")", 0, 1);
                        Thread.Sleep(300);
                        ge.Uygula(ise, me);
                        Durum(S("İngilizce arayüz kuruldu.", "English interface installed."), 1, 1);
                    }
                    else Durum(S("İngilizce arayüz güncel.", "English interface is up to date."), 1, 1);
                }
                else if (ge.KuruluListeOku().Count > 0)
                {
                    Durum(S("İngilizce arayüz kaldırılıyor...", "Removing English interface..."), 0, 1);
                    int n = ge.HepsiniKaldir();
                    Durum(S("İngilizce arayüz kaldırıldı (", "English interface removed (") + n + S(" dosya).", " file(s))."), 1, 1);

                    // Ustune yazdigi metin tablosunu standart depodan geri al.
                    try
                    {
                        var gs = new Guncelleyici(_ayar.Kaynak, _ayar.YedekKaynak,
                                                  _oyunKlasoru, IlerlemeGeldi);
                        Manifest ms = gs.ManifestIndir();
                        List<Is> iss = gs.FarkiCikar(ms);
                        if (iss.Count > 0) gs.Uygula(iss, ms);
                    }
                    catch { }
                    Durum(S("Türkçe arayüze dönüldü.", "Switched back to the Turkish interface."), 1, 1);
                }
            }
            catch (Exception ex)
            {
                string msj = ex.Message;
                Yaz(delegate
                {
                    MessageBox.Show(this,
                        S("İngilizce arayüz paketi alınamadı:\n", "English interface pack could not be fetched:\n") + msj + "\n\n"
                      + S("Oyun mevcut diliyle açılacak. Oyununuza zarar gelmedi;\n", "The game will start in its current language. Nothing was\n")
                      + S("daha sonra tekrar deneyebilirsiniz.", "you can try again later."),
                        S("S2 Launcher · İngilizce arayüz", "S2 Launcher · English interface"),
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                });
            }
        }

        /// <summary>
        /// Secime gore HD paketini kurar ya da kaldirir, sonra
        /// `Default.archcfg`'yi yazar.
        ///
        /// HATA YUTULUYOR: HD deposu cevap vermezse oyun yine de acilmali.
        /// O durumda archcfg diskteki GERCEK duruma gore yaziliyor -
        /// yarim inmis bir paketin satiri archcfg'de kalirsa oyun aciliste
        /// arsivi bulamayip cokerdi.
        /// </summary>
        void HdAsamasi()
        {
            if (!HdVar) { ArchcfgYaz(false); return; }

            bool hdHazir = false;
            try
            {
                var gh = new Guncelleyici(_ayar.HdKaynak, _ayar.HdYedekKaynak,
                                          _oyunKlasoru, IlerlemeGeldi);
                gh.Etiket = "hd";

                if (_hdSecili)
                {
                    Durum(S("HD grafik paketi denetleniyor...", "Checking HD texture pack..."), 0, 1);
                    Manifest mh = gh.ManifestIndir();
                    List<Is> ish = gh.FarkiCikar(mh);
                    if (ish.Count > 0)
                    {
                        long boyut = 0;
                        foreach (var i in ish) if (!i.Silinecek) boyut += i.Boyut;
                        Durum(S("HD paketi indiriliyor (", "Downloading HD pack (") + Bicimle(boyut) + ")", 0, 1);
                        Thread.Sleep(300);
                        gh.Uygula(ish, mh);
                        Durum(S("HD grafik paketi kuruldu.", "HD texture pack installed."), 1, 1);
                    }
                    else Durum(S("HD grafik paketi güncel.", "HD texture pack is up to date."), 1, 1);
                    hdHazir = true;
                }
                else if (gh.KuruluListeOku().Count > 0)
                {
                    Durum(S("HD grafik paketi kaldırılıyor...", "Removing HD texture pack..."), 0, 1);
                    int n = gh.HepsiniKaldir();
                    Durum(S("HD grafik paketi kaldırıldı (", "HD texture pack removed (") + n + S(" dosya).", " file(s))."), 1, 1);
                }
            }
            catch (Exception ex)
            {
                string msj = ex.Message;
                Yaz(delegate
                {
                    MessageBox.Show(this,
                        S("HD grafik paketi alınamadı:\n", "HD texture pack could not be fetched:\n") + msj + "\n\n"
                      + S("Oyun STANDART dokularla açılacak. Oyununuza zarar\n", "The game will start with STANDARD textures. Nothing\n")
                      + S("gelmedi; daha sonra tekrar deneyebilirsiniz.", "was harmed; you can try again later."),
                        S("S2 Launcher · HD paketi", "S2 Launcher · HD pack"),
                        MessageBoxButtons.OK, MessageBoxIcon.Warning);
                });
            }

            // Arsiv satirlari ancak dosyalar GERCEKTEN diskteyse yazilir.
            ArchcfgYaz(_hdSecili && hdHazir && HdArsivleri().Count > 0);
        }

        void IlerlemeGeldi(Ilerleme i)
        {
            string ek = "";
            if (i.DosyaSayisi > 0) ek = "  [" + i.DosyaSirasi + "/" + i.DosyaSayisi + "]";
            string dosya = "";
            int k = i.Durum.LastIndexOf(": ", StringComparison.Ordinal);
            if (k >= 0) dosya = i.Durum.Substring(k + 2);
            string metin = (k >= 0 ? i.Durum.Substring(0, k) : i.Durum) + ek;
            if (i.Toplam > 1024) metin += "   " + Bicimle(i.Yapilan) + " / " + Bicimle(i.Toplam);
            Durum(metin, i.Yapilan, i.Toplam, dosya);
        }

        void Durum(string metin, long yapilan, long toplam) { Durum(metin, yapilan, toplam, null); }
        void Durum(string metin, long yapilan, long toplam, string dosya)
        {
            Yaz(delegate
            {
                _durum = metin;
                if (dosya != null) _dosyaAdi = dosya;
                _ilerleme = toplam > 0 ? (float)yapilan / toplam : 0f;
                Invalidate();
            });
        }

        void DenetimRaporu(Guncelleyici g, Manifest m, List<Is> isler)
        {
            int onarilan = 0, silinen = 0;
            foreach (var i in isler) { if (i.Silinecek) silinen++; else onarilan++; }

            var sb = new StringBuilder();
            sb.AppendLine(S("BÜTÜNLÜK DENETİMİ", "INTEGRITY CHECK"));
            sb.AppendLine();
            sb.AppendLine(S("Denetlenen dosya : ", "Files checked   : ") + m.Dosyalar.Count);
            sb.AppendLine(S("Onarılan         : ", "Repaired        : ") + onarilan);
            sb.AppendLine(S("Silinen (eski sürümden kalan) : ", "Deleted (left from older build): ") + silinen);
            sb.AppendLine(S("Tanınmayan dosya : ", "Unrecognised    : ") + g.YabanciDosyalar.Count);
            sb.AppendLine();
            if (g.YabanciDosyalar.Count > 0)
            {
                sb.AppendLine(S("Oyun klasöründe resmî listede OLMAYAN dosyalar var.", "The game folder contains files that are NOT on the official list."));
                sb.AppendLine(S("Silinmediler - kendi dosyalarınız olabilir:", "They were not deleted - they may be your own files:"));
                sb.AppendLine();
                int y = 0;
                foreach (string yol in g.YabanciDosyalar)
                {
                    if (y++ == 12)
                    {
                        sb.AppendLine(S("   ... ve ", "   ... and ") + (g.YabanciDosyalar.Count - 12) + S(" tane daha", " more"));
                        break;
                    }
                    sb.AppendLine("   " + yol);
                }
                sb.AppendLine();
            }
            if (g.KorunanFarkli.Count == 0)
            {
                sb.AppendLine(onarilan + silinen == 0
                    ? S("Her dosyanın parmak izi resmî sürümle birebir aynı.", "Every file matches the official version exactly.")
                    : S("Bozuk/eksik dosyalar yeniden indirildi.", "Corrupt/missing files were downloaded again."));
            }
            else
            {
                sb.AppendLine(S("Aşağıdakiler resmî sürümden FARKLI, ama bunlar sizin", "The following DIFFER from the official version, but they are your"));
                sb.AppendLine(S("kendi dosyalarınız olduğu için DEĞİŞTİRİLMEDİ:", "own files, so they were NOT changed:"));
                sb.AppendLine();
                int n = 0;
                foreach (string y in g.KorunanFarkli)
                {
                    if (n++ == 12) { sb.AppendLine(S("   ... ve ", "   ... and ") + (g.KorunanFarkli.Count - 12) + S(" tane daha", " more")); break; }
                    sb.AppendLine("   " + y);
                }
                sb.AppendLine();
                sb.AppendLine(S("Kendiniz değiştirdiyseniz normaldir.", "If you changed them yourself, this is normal."));
            }
            string metin = sb.ToString();
            Yaz(delegate
            {
                MessageBox.Show(this, metin, S("S2 Launcher · Bütünlük Denetimi", "S2 Launcher · Integrity Check"),
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
            });
        }

        void Yaz(Action a)
        {
            if (IsDisposed) return;
            try { if (InvokeRequired) BeginInvoke(a); else a(); } catch { }
        }

        static string Bicimle(long b)
        {
            if (b >= 1L << 30) return (b / (double)(1L << 30)).ToString("0.00") + " GB";
            if (b >= 1L << 20) return (b / (double)(1L << 20)).ToString("0.0") + " MB";
            if (b >= 1L << 10) return (b / (double)(1L << 10)).ToString("0") + " KB";
            return b + " B";
        }

        // -----------------------------------------------------------------
        //  HABERLER
        // -----------------------------------------------------------------
        void HaberleriYukle()
        {
            try
            {
                ServicePointManager.SecurityProtocol =
                    SecurityProtocolType.Tls12 | SecurityProtocolType.Tls11;
                // Haber paneli kritik degil: ana adres cevap vermezse sessizce
                // yedege dusuyoruz, o da yoksa panel bos kalir (oyun acilir).
                string ham = null;
                var adresler = new List<string> { _ayar.Kaynak };
                if (!string.IsNullOrEmpty(_ayar.YedekKaynak)) adresler.Add(_ayar.YedekKaynak);
                foreach (var kaynak in adresler)
                {
                    try
                    {
                        var istek = (HttpWebRequest)WebRequest.Create(
                            kaynak.TrimEnd('/') + "/news.json?t=" + DateTime.UtcNow.Ticks);
                        istek.Timeout = 8000;
                        istek.UserAgent = "S2Launcher";
                        using (var y = istek.GetResponse())
                        using (var s = new StreamReader(y.GetResponseStream(), Encoding.UTF8))
                            ham = s.ReadToEnd();
                        break;
                    }
                    catch { }
                }
                if (ham == null) return;

                var js = new JavaScriptSerializer();
                var kok = (Dictionary<string, object>)js.DeserializeObject(ham);
                if (!kok.ContainsKey("haberler")) return;

                var satirlar = new List<string[]>();
                foreach (var o in (object[])kok["haberler"])
                {
                    var h = (Dictionary<string, object>)o;
                    satirlar.Add(new[] {
                        h.ContainsKey("tarih")    ? Convert.ToString(h["tarih"])    : "",
                        h.ContainsKey("baslik")   ? Convert.ToString(h["baslik"])   : "",
                        h.ContainsKey("aciklama") ? Convert.ToString(h["aciklama"]) : "",
                        h.ContainsKey("adres")    ? Convert.ToString(h["adres"])    : ""
                    });
                }
                Yaz(delegate { _haberler = satirlar; Invalidate(); });
            }
            catch
            {
                Yaz(delegate
                {
                    _haberler = new List<string[]> {
                        new[] { "", S("Haberler alınamadı", "News could not be loaded"), S("Sunucuya ulaşılamıyor.", "The server cannot be reached."), "" } };
                    Invalidate();
                });
            }
        }

        void AdresAc(string adres)
        {
            // Yalnizca http/https - "file:", "cmd:" gibi semalar calistirilmaz.
            if (string.IsNullOrEmpty(adres)) return;
            if (!adres.StartsWith("http://", StringComparison.OrdinalIgnoreCase)
                && !adres.StartsWith("https://", StringComparison.OrdinalIgnoreCase)) return;
            try { Process.Start(adres); } catch { }
        }

        void KendiniYenidenBaslat()
        {
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = System.Reflection.Assembly.GetExecutingAssembly().Location,
                    WorkingDirectory = Program.KendiKlasoru(),
                    UseShellExecute = false
                });
            }
            catch { }
            Application.Exit();
        }

        // -----------------------------------------------------------------
        //  OYUNU BASLAT
        // -----------------------------------------------------------------
        void OyunuBaslat()
        {
            string exe = Path.Combine(_oyunKlasoru, _ayar.Exe);
            if (!File.Exists(exe))
            {
                MessageBox.Show(S("Oyun dosyası bulunamadı:\n", "Game executable not found:\n") + exe,
                    "S2 Launcher", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // ---- NEDEN UseShellExecute = true ----------------------------
            // TheRaw.exe'nin gomulu manifestinde
            //     requestedExecutionLevel = requireAdministrator
            // yaziyor - oyun YONETICI olarak acilmak zorunda. UseShellExecute
            // = false kipinde Windows yukseltme YAPAMAZ ve "Istenen islem icin
            // yukseltme gerekiyor" (hata 740) doner. Yukseltmeyi yalnizca
            // ShellExecute yapabilir; UAC penceresini o cikarir.
            var psi = new ProcessStartInfo
            {
                FileName = exe,
                WorkingDirectory = _oyunKlasoru,
                Arguments = string.Join(" ", _ayar.Argumanlar()),
                UseShellExecute = true
            };
            try
            {
                // ---- NOBETCI (2026-08-17) --------------------------------
                // ONCEDEN: oyunu ac, kendini KAPAT. Oyun coktugunde geriye
                // hicbir sey kalmiyordu - ne cikis kodu, ne sure, ne de
                // Windows'un yazdigi dokumu toplayan biri.
                //
                // SIMDI: launcher gizlenip arkada bekliyor. Oyun kapaninca
                // anormal bitis mi diye bakiyor (yeni dokum belirdi mi,
                // cikis kodu sifir mi) ve gerekiyorsa raporu yolluyor.
                // NORMAL oyunda tek bayt gitmiyor.
                //
                // `tani` adresi bos ise (ya da oyuncu `tani_gonder = 0`
                // yazmissa) eski davranis birebir korunuyor: ac ve kapan.
                bool taniAcik = Tani.Acik(_ayar);
                bool discordAcik = DiscordVarlik.Etkin(_ayar);
                // ⚠ APEX KOPRUSU DE NOBETCI ISTIYOR (K-392, 08.09.2026):
                //   Kopru bu surecte yasiyor. Asagidaki "ac ve kapan" dali
                //   secilirse `ApexKanal.Basla` satirina HIC ULASILMIYOR ve
                //   anti-hile bulgulari sunucuya gitmiyor.
                //
                //   Canlida tam olarak bu oluyordu: `tani` bos (K-391),
                //   `discord_uygulama` bos -> ikisi de false -> launcher
                //   oyunu acip oluyordu. ApexGuard ihlali yakalayip oyunu
                //   kapatiyor ama panele hicbir sey dusmuyordu.
                //
                //   Belirti "hicbir sey olmamasi" oldugu icin sessizdi.
                //   Yeni bir "launcher hayatta kalmali" ozelligi eklenirse
                //   KOSULA EKLENMESI GEREKIYOR.
                bool apexAcik = ApexKanal.Etkin(_ayar);
                if (!taniAcik && !discordAcik && !apexAcik)
                {
                    Process.Start(psi);
                    Close();
                    return;
                }

                // Discord varligi da ayni nobetci yolu kullanir: launcher gizli
                // bekler, oyun kapaninca Discord'daki durumu siler (DiscordVarlik.cs).
                var seans = taniAcik ? Tani.Basla(_oyunKlasoru, _ayar) : null;
                Process surec = Process.Start(psi);
                // Ag izi surec DOGDUKTAN sonra baslar - oyunun kendi
                // sayaclarini okuyacak ([[AgIzi]]). Oyuna dokunmaz.
                if (seans != null) Tani.AgIziBasla(seans, surec);
                // ---- ANTI-HILE RAPOR KOPRUSU ([[ApexKanal]]) ------------
                // ApexGuard oyun surecinde paylasimli bellege yaziyor; kopru
                // onu okuyup sunucuya tasiyor. Oyun surecinde ag/disk isi YOK.
                //
                // ⚠ OYUNCU ADI GONDERMIYORUZ CUNKU BILMIYORUZ: oyun hesabina
                //   giris launcher'da degil OYUNUN ICINDE yapiliyor. Elimizde
                //   yalnizca (varsa) Discord adi var, o da yalnizca IPUCU.
                //   Kimligi sunucu IP+ZAMAN ile cozuyor (`kimlik-coz.js`) -
                //   burada uydurmak yanlis eslesme uretirdi.
                ApexKanal apexKopru = _ayar.ApexGonder
                    ? ApexKanal.Basla(_ayar.Apex, surec, _ayar.DiscordKullanici)
                    : null;
                if (discordAcik) DiscordVarlik.Baslat(_ayar, surec, Path.GetFileNameWithoutExtension(_ayar.Exe));

                // Pencereyi kapatmiyoruz ama gostermiyoruz da; gorev
                // cubugunda da durmasin - oyuncu icin hicbir sey degismis
                // gorunmesin.
                Hide();
                ShowInTaskbar = false;

                new Thread(delegate ()
                {
                    int kod = 0;
                    try
                    {
                        if (surec != null)
                        {
                            surec.WaitForExit();
                            // Yukseltilmis surecin cikis kodu okunamayabilir
                            // (UAC ile acildi, tanitici sinirli). Okunamazsa
                            // 0 sayiyoruz - yanlis alarm uretmemek icin.
                            try { kod = surec.ExitCode; } catch { kod = 0; }
                        }
                        else
                        {
                            // ShellExecute bazen surec nesnesi dondurmuyor
                            // (kabuk var olan bir sureci kullanirsa).
                            // O zaman ada gore bekliyoruz.
                            SureciAdlaBekle(Path.GetFileNameWithoutExtension(_ayar.Exe));
                        }
                        DiscordVarlik.Durdur();
                        // ⚠ SIRA: kopru `Tani.Bitir`DEN ONCE kapanmali ve
                        //   kendi icinde ONCE OKUYUP sonra eslemeyi birakmali.
                        //   ApexGuard ihlalde oyunu oldurup kaydi birakiyor;
                        //   paylasimli bellek SON TUTAMAK kapaninca yok oluyor.
                        //   Erken kapatirsak ihlal kaydi buharlasir.
                        //   Sinandi: apex_kanal_sinav.cpp "olum sonrasi kanit".
                        if (apexKopru != null) apexKopru.Bitir();
                        if (seans != null) Tani.Bitir(seans, kod);
                    }
                    catch { }
                    // Launcher'in isi bitti. `Invoke` gerekiyor: pencereyi
                    // yaratan is parcacigi bu degil.
                    try { BeginInvoke((Action)(() => { Close(); Application.Exit(); })); }
                    catch { Environment.Exit(0); }
                })
                { IsBackground = false }.Start();
                return;
            }
            catch (System.ComponentModel.Win32Exception w)
            {
                // 1223 = ERROR_CANCELLED: oyuncu UAC penceresinde "Hayir" dedi.
                // Hata degil, tercih - launcher acik kalsin.
                if (w.NativeErrorCode == 1223)
                {
                    _hata = true;
                    _durum = S("Yönetici izni verilmedi. Oyun yönetici olarak açılmak zorunda.", "Administrator permission was denied. The game must run as administrator.");
                    Invalidate();
                    return;
                }
                MessageBox.Show(S("Oyun başlatılamadı:\n", "The game could not be started:\n") + w.Message,
                    "S2 Launcher", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            catch (Exception ex)
            {
                MessageBox.Show(S("Oyun başlatılamadı:\n", "The game could not be started:\n") + ex.Message,
                    "S2 Launcher", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        /// <summary>
        /// `Process.Start` nesne dondurmediginde kullanilan yedek yol:
        /// oyunun surecini ADIYLA bulup bitmesini bekler. Once dogmasini
        /// bekliyoruz (UAC penceresinde oyalanan oyuncu icin 60 sn), sonra
        /// kaybolmasini.
        /// </summary>
        static void SureciAdlaBekle(string ad)
        {
            Process oyun = null;
            for (int i = 0; i < 120 && oyun == null; i++)
            {
                try
                {
                    Process[] bulunan = Process.GetProcessesByName(ad);
                    if (bulunan.Length > 0) oyun = bulunan[0];
                }
                catch { }
                if (oyun == null) Thread.Sleep(500);
            }
            if (oyun == null) return;
            try { oyun.WaitForExit(); } catch { }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            if (_mesgul && e.CloseReason == CloseReason.UserClosing)
            {
                if (MessageBox.Show(S("Güncelleme sürüyor. Yine de kapatılsın mı?", "An update is in progress. Close anyway?"),
                        "S2 Launcher", MessageBoxButtons.YesNo,
                        MessageBoxIcon.Question) != DialogResult.Yes)
                { e.Cancel = true; return; }
            }
            base.OnFormClosing(e);
        }
    }
}
