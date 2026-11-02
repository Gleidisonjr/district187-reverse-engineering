// =====================================================================
//  DISCORD RICH PRESENCE  (03.09.2026)
//
//  Oyun acikken Discord'da "S2 Rebirth oynuyor · Ghost City · Raunt 3/10"
//  yazar. Iki parca:
//
//    1. DURUM  - portal: GET <site>/api/oyuncu/varlik?jeton=...  (5 sn'de bir)
//       Jeton BIR KEZ alinir ve launcher-ozel.cfg'de durur. Iki yol:
//         a) 12.09.2026'dan beri VARSAYILAN: launcher'daki Discord simgesi ->
//            oyun hesabi adi + sifre -> POST /discord-giris -> jeton (`Giris`).
//            Sifre yalniz o istekte gider, launcher SAKLAMAZ.
//         b) eski yol: sitedeki "Discord'da goster" kutusundan 6 haneli kod
//            -> POST /discord-esle (`Esle`). Sunucu (a)'yi bilmiyorsa (404)
//            pencere kendiliginden (b)'ye gecer.
//       Jeton YALNIZ bu hesabin durumunu okutur; cevapta oda adi, baska
//       oyuncu, adres yoktur (sunucu tarafi: portal/api.js `varlik`).
//
//    2. DISCORD - bilgisayardaki Discord istemcisinin yerel borusu
//       \\.\pipe\discord-ipc-N. Internete cikan hicbir sey yok. Discord
//       kapaliysa sessizce bekler, 15 sn'de bir yeniden dener.
//
//  Launcher oyun kapanana kadar gizli bekler (Tani ile ayni "nobetci"
//  yolu, AnaPencere.OyunuBaslat). `discord_uygulama` (Discord Application
//  ID, launcher.cfg) bos ise ozellik hic gorunmez; oyuncu acmadiysa
//  (`discord = 1`) hicbir sey calismaz.
//
//  Boru cerceve bicimi (Discord RPC): 4 bayt LE opcode + 4 bayt LE uzunluk
//  + UTF-8 JSON. Opcode 0 el sikisma, 1 cerceve, 2 kapat, 3 ping, 4 pong.
//  SET_ACTIVITY en fazla 15 sn'de bir islenir; bu yuzden yalniz DEGISEN
//  durum gonderilir.
// =====================================================================
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Pipes;
using System.Net;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace S2Launcher
{
    /// <summary>
    /// Baglama penceresi (AnaPencere.DiscordEsleAc). Iki kip:
    ///   GIRIS (varsayilan): oyun hesabi adi + sifre -> `DiscordVarlik.Giris`.
    ///   KOD: sitedeki "Discord'da goster" kutusundan 6 haneli kod -> `Esle`.
    /// Sunucu /discord-giris'i tanimiyorsa (eski surum, 404) KOD kipine
    /// kendiliginden gecer. Sonuc: Jeton + Kullanici, launcher-ozel.cfg'ye
    /// AnaPencere yazar. Sifre hicbir yere yazilmaz.
    /// </summary>
    public class DiscordBaglaPenceresi : Form
    {
        readonly Ayarlar _ayar;
        readonly Label _aciklama, _adEtiket, _sifreEtiket, _durum;
        readonly TextBox _ad, _sifre, _kod;
        readonly Button _bagla;
        readonly LinkLabel _kipDegistir;
        bool _kodKipi;
        public string Jeton = "";
        public string Kullanici = "";

        public DiscordBaglaPenceresi(Ayarlar ayar)
        {
            _ayar = ayar;
            Text = AnaPencere.S("Discord'a bağla", "Link Discord");
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterParent;
            MaximizeBox = false;
            MinimizeBox = false;
            ShowInTaskbar = false;
            ClientSize = new Size(460, 318);
            BackColor = Color.FromArgb(18, 18, 20);
            ForeColor = Color.FromArgb(228, 228, 232);
            Font = new Font("Segoe UI", 9.5f);

            _aciklama = new Label { AutoSize = false, Bounds = new Rectangle(20, 14, 420, 78) };
            _adEtiket = new Label { AutoSize = true, Location = new Point(20, 100), Text = AnaPencere.S("Kullanıcı adı", "Username"), ForeColor = Color.FromArgb(170, 170, 178) };
            _ad = Kutu(new Rectangle(20, 120, 200, 30), 32);
            if (ayar != null && ayar.DiscordKullanici.Length > 0) _ad.Text = ayar.DiscordKullanici;
            _sifreEtiket = new Label { AutoSize = true, Location = new Point(240, 100), Text = AnaPencere.S("Şifre", "Password"), ForeColor = Color.FromArgb(170, 170, 178) };
            _sifre = Kutu(new Rectangle(240, 120, 200, 30), 64);
            _sifre.UseSystemPasswordChar = true;
            _kod = Kutu(new Rectangle(20, 120, 170, 34), 7);
            _kod.Font = new Font("Consolas", 16f);
            _kod.TextAlign = HorizontalAlignment.Center;

            _bagla = new Button
            {
                Bounds = new Rectangle(20, 166, 220, 36),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(88, 101, 242),   // Discord mavisi
                ForeColor = Color.White,
            };
            _bagla.FlatAppearance.BorderSize = 0;
            var vazgec = new Button
            {
                Text = AnaPencere.S("Vazgeç", "Cancel"),
                Bounds = new Rectangle(336, 166, 104, 36),
                FlatStyle = FlatStyle.Flat,
                DialogResult = DialogResult.Cancel,
                ForeColor = Color.FromArgb(200, 200, 208),
            };
            vazgec.FlatAppearance.BorderColor = Color.FromArgb(70, 70, 78);
            _durum = new Label
            {
                AutoSize = false,
                Bounds = new Rectangle(20, 212, 420, 62),
                ForeColor = Color.FromArgb(150, 150, 158),
            };
            _kipDegistir = new LinkLabel
            {
                AutoSize = true,
                Location = new Point(20, 286),
                LinkColor = Color.FromArgb(150, 160, 255),
                ActiveLinkColor = Color.White,
                VisitedLinkColor = Color.FromArgb(150, 160, 255),
                LinkBehavior = LinkBehavior.HoverUnderline,
            };
            _kipDegistir.LinkClicked += delegate { KipAyarla(!_kodKipi); };
            _bagla.Click += delegate { Bagla(); };
            AcceptButton = _bagla;
            CancelButton = vazgec;
            Controls.AddRange(new Control[] { _aciklama, _adEtiket, _ad, _sifreEtiket, _sifre, _kod, _bagla, vazgec, _durum, _kipDegistir });
            KipAyarla(false);
        }

        static TextBox Kutu(Rectangle r, int enUzun)
        {
            return new TextBox
            {
                Bounds = r,
                MaxLength = enUzun,
                BackColor = Color.FromArgb(30, 30, 34),
                ForeColor = Color.White,
                BorderStyle = BorderStyle.FixedSingle,
                Font = new Font("Segoe UI", 11f),
            };
        }

        void KipAyarla(bool kod)
        {
            _kodKipi = kod;
            _adEtiket.Visible = _ad.Visible = _sifreEtiket.Visible = _sifre.Visible = !kod;
            _kod.Visible = kod;
            _aciklama.Text = kod
                ? AnaPencere.S(
                    "s2rebirth.com'da giriş yap → Hesabım → \"Discord'da göster\" → Kod al.\n" +
                    "Kodu aşağıya yaz ve Bağla'ya bas. Kod 15 dakika geçerli, tek kullanımlık.",
                    "Sign in at s2rebirth.com → My account → \"Show on Discord\" → Get code.\n" +
                    "Enter the code below and press Link. Valid for 15 minutes, single use.")
                : AnaPencere.S(
                    "Oyun hesabınla giriş yap; oyundayken Discord'da \"S2 Rebirth oynuyor · harita · raunt\" görünsün.\n" +
                    "Şifren yalnızca s2rebirth.com'a gider, launcher saklamaz. Paylaşılan tek şey kendi durumun; " +
                    "istediğin an kapatabilirsin.",
                    "Sign in with your game account; while playing, Discord shows \"Playing S2 Rebirth · map · round\".\n" +
                    "Your password is sent only to s2rebirth.com and never stored by the launcher. Only your own " +
                    "status is shared; you can turn it off any time.");
            _bagla.Text = kod ? AnaPencere.S("Bağla", "Link") : AnaPencere.S("Giriş yap ve bağla", "Sign in and link");
            _kipDegistir.Text = kod
                ? AnaPencere.S("Kullanıcı adı ve şifreyle bağla", "Link with username and password")
                : AnaPencere.S("Siteden aldığın 6 haneli kodla bağla", "Link with a 6-digit code from the site");
            _durum.Text = "";
            if (kod) _kod.Focus();
            else if (_ad.Text.Length > 0) _sifre.Focus();
            else _ad.Focus();
        }

        void Bagla()
        {
            bool kodKipi = _kodKipi;
            string kod = _kod.Text, ad = _ad.Text.Trim(), sifre = _sifre.Text;
            if (!kodKipi && (ad.Length == 0 || sifre.Length == 0))
            {
                _durum.Text = AnaPencere.S("Kullanıcı adı ve şifre boş olamaz.", "Username and password are required.");
                return;
            }
            Kilitle(false);
            _durum.Text = AnaPencere.S("Sunucuya soruluyor…", "Asking the server…");
            var t = new Thread(delegate ()
            {
                var s = kodKipi ? DiscordVarlik.Esle(_ayar, kod) : DiscordVarlik.Giris(_ayar, ad, sifre);
                try
                {
                    BeginInvoke((Action)(delegate ()
                    {
                        if (s.Ok)
                        {
                            Jeton = s.Jeton;
                            Kullanici = s.Kullanici;
                            DialogResult = DialogResult.OK;
                            Close();
                            return;
                        }
                        Kilitle(true);
                        if (s.KodaGec && !_kodKipi)
                        {
                            // Eski sunucu: giris ucu yok -> kod kipi, mesaj kalsin.
                            KipAyarla(true);
                        }
                        _durum.Text = s.Hata;
                        if (_kodKipi) _kod.Focus(); else _sifre.Focus();
                    }));
                }
                catch { }
            })
            { IsBackground = true };
            t.Start();
        }

        void Kilitle(bool acik)
        {
            _bagla.Enabled = _ad.Enabled = _sifre.Enabled = _kod.Enabled = _kipDegistir.Enabled = acik;
        }
    }

    public static class DiscordVarlik
    {
        static Thread _is;
        static volatile bool _dur;
        static readonly JavaScriptSerializer Js = new JavaScriptSerializer();

        /// <summary>Ozellik bu oyuncu icin calisacak mi (acik + uygulama + jeton).</summary>
        public static bool Etkin(Ayarlar a)
        {
            return a != null && a.Discord
                && a.DiscordUygulama.Trim().Length > 0
                && a.DiscordJeton.Trim().Length > 0;
        }

        /// <summary>Uygulama kimligi tanimli mi - arayuzde secenek gorunsun mu.</summary>
        public static bool Tanimli(Ayarlar a)
        {
            return a != null && a.DiscordUygulama.Trim().Length > 0;
        }

        public static void Baslat(Ayarlar a, Process oyun, string exeAdi)
        {
            Durdur();
            _dur = false;
            _is = new Thread(delegate () { Calis(a, oyun, exeAdi); })
            { IsBackground = true, Name = "discord-varlik" };
            _is.Start();
        }

        public static void Durdur()
        {
            _dur = true;
            var t = _is;
            _is = null;
            if (t != null) { try { t.Join(4000); } catch { } }
        }

        /// <summary>
        /// SINAV KANCASI (tools/discord-boru-sinav): bilgisayardaki Discord'a
        /// el sikisip sonucu yazar; SET_ACTIVITY GONDERMEZ. Uygulama kimligi
        /// gecersizse Discord op=2 ile reddeder - cerceve bicimi yine olculmus olur.
        /// </summary>
        public static string BoruSinavi(string uygulama)
        {
            var b = DiscordBoru.Bagla(uygulama);
            if (b == null) return "bagli-degil";
            b.Kapat();
            return "hazir";
        }

        /// <summary>SINAV KANCASI: durum sozlugunden SET_ACTIVITY cercevesi.</summary>
        public static string EtkinlikSinavi(string durumJson, int pid, long acilis)
        {
            var d = Js.DeserializeObject(durumJson) as Dictionary<string, object>;
            return EtkinlikJson(d, pid, acilis);
        }

        // -----------------------------------------------------------------
        //  ESLESTIRME  (launcher -> portal, oturumsuz)
        // -----------------------------------------------------------------

        public class EslesmeSonucu
        {
            public bool Ok; public string Hata = ""; public string Jeton = ""; public string Kullanici = "";
            /// <summary>Sunucu /discord-giris'i tanimiyor (404): pencere kod kipine gecsin.</summary>
            public bool KodaGec;
        }

        /// <summary>
        /// 12.09.2026: oyun hesabi adi + sifre ile dogrudan jeton. Sunucu
        /// tarafi `portal/sunucu.js /discord-giris` (oturumsuz, /giris ile
        /// ayni IP+ad hiz siniri, Turnstile YOK - launcher'da tarayici yok).
        /// Cevap yalniz varlik jetonu; site oturumu ACILMAZ, cerez donmez.
        /// </summary>
        public static EslesmeSonucu Giris(Ayarlar a, string ad, string sifre)
        {
            var s = new EslesmeSonucu();
            ad = (ad ?? "").Trim();
            if (ad.Length == 0 || string.IsNullOrEmpty(sifre))
            {
                s.Hata = AnaPencere.S("Kullanıcı adı ve şifre boş olamaz.", "Username and password are required.");
                return s;
            }
            var govde = new Dictionary<string, object> { { "ad", ad }, { "sifre", sifre } };
            return Gonder(a, "/api/oyuncu/discord-giris", Js.Serialize(govde), s);
        }

        /// <summary>Sitedeki 6 haneli kodu jetona cevirir. Ag hatasi = Ok=false + mesaj.</summary>
        public static EslesmeSonucu Esle(Ayarlar a, string kod)
        {
            var s = new EslesmeSonucu();
            string temiz = "";
            foreach (char c in kod ?? "") if (char.IsDigit(c)) temiz += c;
            if (temiz.Length != 6) { s.Hata = AnaPencere.S("Kod 6 haneli olmalı.", "The code must be 6 digits."); return s; }
            return Gonder(a, "/api/oyuncu/discord-esle", "{\"kod\":\"" + temiz + "\"}", s);
        }

        /// <summary>Portala JSON POST; {jeton, kullanici} -> Ok, {hata} -> mesaj. 404 -> KodaGec.</summary>
        static EslesmeSonucu Gonder(Ayarlar a, string yol, string json, EslesmeSonucu s)
        {
            try
            {
                ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
                var istek = (HttpWebRequest)WebRequest.Create(SiteKoku(a) + yol);
                istek.Method = "POST";
                istek.ContentType = "application/json";
                istek.UserAgent = "S2Launcher";
                istek.Timeout = 10000;
                byte[] govde = Encoding.UTF8.GetBytes(json);
                using (var st = istek.GetRequestStream()) st.Write(govde, 0, govde.Length);
                string cevap = CevapOku(istek);
                var d = Js.DeserializeObject(cevap) as Dictionary<string, object>;
                if (d != null && d.ContainsKey("jeton"))
                {
                    s.Ok = true;
                    s.Jeton = Convert.ToString(d["jeton"]);
                    s.Kullanici = d.ContainsKey("kullanici") ? Convert.ToString(d["kullanici"]) : "";
                    return s;
                }
                s.Hata = (d != null && d.ContainsKey("hata")) ? Convert.ToString(d["hata"]) : AnaPencere.S("Beklenmeyen cevap.", "Unexpected response.");
            }
            catch (WebException w)
            {
                string metin = null;
                var r = w.Response as HttpWebResponse;
                try { if (w.Response != null) metin = CevapOku(w.Response); } catch { }
                var d = metin == null ? null : Js.DeserializeObject(metin) as Dictionary<string, object>;
                if (r != null && (int)r.StatusCode == 404)
                {
                    // Sunucu bu ucu bilmiyor (eski surum). Kod yolu her zaman var.
                    s.KodaGec = true;
                    s.Hata = AnaPencere.S(
                        "Sunucu henüz bu girişi desteklemiyor. Siteden aldığın 6 haneli kodla bağla.",
                        "The server does not support this sign-in yet. Link with a 6-digit code from the site.");
                }
                else if (d != null && d.ContainsKey("hata")) s.Hata = Convert.ToString(d["hata"]);
                else s.Hata = AnaPencere.S("Sunucuya ulaşılamadı: ", "Could not reach the server: ") + w.Message;
            }
            catch (Exception e) { s.Hata = e.Message; }
            return s;
        }

        static string SiteKoku(Ayarlar a)
        {
            string site = (a.Site ?? "").Trim();
            if (site.Length == 0) site = "https://s2rebirth.com";
            return site.TrimEnd('/');
        }

        static string CevapOku(HttpWebRequest istek)
        {
            using (var c = istek.GetResponse()) return CevapOku(c);
        }

        static string CevapOku(WebResponse c)
        {
            using (var st = c.GetResponseStream())
            using (var r = new StreamReader(st, Encoding.UTF8)) return r.ReadToEnd();
        }

        // -----------------------------------------------------------------
        //  ANA DONGU
        // -----------------------------------------------------------------

        static void Calis(Ayarlar a, Process oyun, string exeAdi)
        {
            try { ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12; } catch { }
            long acilis = UnixSaniye(DateTime.UtcNow);
            int pid = 0;
            try { if (oyun != null) pid = oyun.Id; } catch { }
            if (pid == 0) pid = Process.GetCurrentProcess().Id;

            DiscordBoru boru = null;
            DateTime sonBoruDeneme = DateTime.MinValue;
            DateTime sonSorgu = DateTime.MinValue;
            string site = SiteKoku(a);
            string etkinlik = EtkinlikJson(null, pid, acilis, site);
            string gonderilen = null;
            int ustUsteHata = 0;
            bool jetonGecersiz = false;

            Gunluk("basladi pid=" + pid);
            while (!_dur)
            {
                try
                {
                    if (OyunBitti(oyun, exeAdi)) { Gunluk("oyun kapandi"); break; }

                    if (!jetonGecersiz && (DateTime.UtcNow - sonSorgu).TotalSeconds >= 5)
                    {
                        sonSorgu = DateTime.UtcNow;
                        int kod;
                        var durum = DurumAl(a, out kod);
                        if (kod == 401)
                        {
                            // Jeton iptal edilmis (sitede "Baglantiyi kes"). Ayrintisiz
                            // "oynuyor" ile devam, bir daha sormuyoruz.
                            jetonGecersiz = true;
                            Gunluk("jeton gecersiz - ayrintisiz kip");
                            etkinlik = EtkinlikJson(null, pid, acilis, site);
                        }
                        else if (durum != null)
                        {
                            ustUsteHata = 0;
                            etkinlik = EtkinlikJson(durum, pid, acilis, site);
                        }
                        else
                        {
                            ustUsteHata++;
                            if (ustUsteHata == 3) Gunluk("durum alinamiyor (3 kez)");
                        }
                    }

                    if (boru == null && (DateTime.UtcNow - sonBoruDeneme).TotalSeconds >= 15)
                    {
                        sonBoruDeneme = DateTime.UtcNow;
                        boru = DiscordBoru.Bagla(a.DiscordUygulama.Trim());
                        gonderilen = null;
                        if (boru != null) Gunluk("discord borusu bagli");
                    }

                    if (boru != null)
                    {
                        if (!boru.Dinle()) { Gunluk("boru koptu"); boru.Kapat(); boru = null; }
                        else if (etkinlik != gonderilen)
                        {
                            if (boru.Gonder(etkinlik)) gonderilen = etkinlik;
                            else { Gunluk("gonderilemedi"); boru.Kapat(); boru = null; }
                        }
                    }
                }
                catch (Exception e) { Gunluk("dongu: " + e.Message); }
                Thread.Sleep(1000);
            }

            if (boru != null)
            {
                try { boru.Gonder(TemizJson(pid)); } catch { }
                boru.Kapat();
            }
            Gunluk("bitti");
        }

        static bool OyunBitti(Process oyun, string exeAdi)
        {
            if (oyun != null)
            {
                try { return oyun.HasExited; } catch { }
            }
            // ShellExecute surec nesnesi vermediyse ada gore bak.
            try { return Process.GetProcessesByName(exeAdi).Length == 0; } catch { return false; }
        }

        // -----------------------------------------------------------------
        //  PORTAL SORGUSU
        // -----------------------------------------------------------------

        static Dictionary<string, object> DurumAl(Ayarlar a, out int kod)
        {
            kod = 0;
            try
            {
                var istek = (HttpWebRequest)WebRequest.Create(
                    SiteKoku(a) + "/api/oyuncu/varlik?jeton=" + Uri.EscapeDataString(a.DiscordJeton.Trim()));
                istek.Method = "GET";
                istek.UserAgent = "S2Launcher";
                istek.Timeout = 8000;
                string cevap = CevapOku(istek);
                kod = 200;
                return Js.DeserializeObject(cevap) as Dictionary<string, object>;
            }
            catch (WebException w)
            {
                var r = w.Response as HttpWebResponse;
                if (r != null) kod = (int)r.StatusCode;
                return null;
            }
            catch { return null; }
        }

        // -----------------------------------------------------------------
        //  ETKINLIK METNI
        // -----------------------------------------------------------------

        static string Metin(Dictionary<string, object> d, string k)
        {
            object v;
            return d != null && d.TryGetValue(k, out v) && v != null ? Convert.ToString(v) : "";
        }

        static long Sayi(Dictionary<string, object> d, string k)
        {
            object v;
            if (d == null || !d.TryGetValue(k, out v) || v == null) return 0;
            try { return Convert.ToInt64(v); } catch { return 0; }
        }

        static long UnixSaniye(DateTime t)
        {
            return (long)(t - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds;
        }

        /// <summary>
        /// SET_ACTIVITY cercevesi. `durum` null = ayrintisiz "oynuyor".
        ///
        /// ---- 12.09.2026 (gece): AYRINTILI GORUNUM ------------------------
        /// Discord'un verdigi yerler ve bizim doldurdugumuz (olculdu, Discord
        /// SET_ACTIVITY cevabinda aynen yankilandi):
        ///   details (1. satir)  : harita · mod   /  "Klan Maçı A vs B"
        ///   state   (2. satir)  : "Round 5/5 · Çete 3–1 Özel Tim · 12/7"
        ///   party.size          : "(4 of 16)" - 2. satirin sonuna Discord ekler
        ///   timestamps.end      : "01:48 left" geri sayim (raunt/mac saati);
        ///                         yoksa timestamps.start = gecen sure
        ///   large_text (tooltip): "S2 Rebirth · harita · mod · Rauntlar: Ç ÖT Ç"
        ///   small_text (tooltip): "Çete tarafında · 12 öldürme / 7 ölüm"
        ///   buttons             : s2rebirth.com (BASKALARINA gorunur, kendine degil)
        /// Sunucu alanlari: haritaTr/modTr, raunt/toplamRaunt/hedefRaunt,
        /// skor (raunt), takimSkoru, hedefSkor, oda{kisi,kapasite}, klanMaci/
        /// klanAd1/klanAd2 (12.09 aksam) + takim/oldurme/olum/rauntGecmisi/
        /// geriSayimBitis (12.09 gece, sunucu guncellenince). Olmayan alan =
        /// o parca cizilmez; eski sunucuyla da calisir.
        /// Takim adlari: oda takimi 1 = Çete (GlobalUI_strGangsters), 2 =
        /// Özel Tim (GlobalUI_strSWAT); klan macinda klan adlari.
        /// </summary>
        static string EtkinlikJson(Dictionary<string, object> d, int pid, long acilis, string site = "https://s2rebirth.com")
        {
            string durum = Metin(d, "durum");
            string harita = Metin(d, "haritaTr");
            if (harita.Length == 0) harita = Metin(d, "harita");
            string mod = Metin(d, "modTr");
            if (mod.Length == 0) mod = Metin(d, "mod");
            string ayrinti;
            string hal = null;
            string kucuk = "lobi";
            string buyukMetin = "S2 Rebirth";
            string kucukMetin = null;
            long baslangic = acilis;
            long bitis = 0;
            long[] parti = null;

            object odaNesne;
            var oda = d != null && d.TryGetValue("oda", out odaNesne) ? odaNesne as Dictionary<string, object> : null;
            long kisi = Sayi(oda, "kisi"), kapasite = Sayi(oda, "kapasite");
            if (kapasite > 0 && kisi >= 0) parti = new[] { kisi, kapasite };

            if (durum == "lobi")
                ayrinti = AnaPencere.S("Lobide", "In the lobby");
            else if (durum == "dukkan")
                ayrinti = AnaPencere.S("Dükkanda", "In the shop");
            else if (durum == "oda")
            {
                ayrinti = AnaPencere.S("Odada bekliyor", "Waiting in a room");
                hal = HaritaMod(harita, mod);
                // Kisi sayisini party.size gosterir ("(3 of 8)"); Discord bunu
                // yalniz `state` varken cizer - harita bilinmiyorsa metne yaz.
                if (parti != null && hal.Length == 0) hal = kisi + "/" + kapasite;
                if (hal.Length == 0) hal = null;
                buyukMetin = "S2 Rebirth" + (HaritaMod(harita, mod).Length > 0 ? " · " + HaritaMod(harita, mod) : "");
            }
            else if (durum == "macta")
            {
                kucuk = "mac";
                long raunt = Sayi(d, "raunt"), toplam = Sayi(d, "toplamRaunt"), hedef = Sayi(d, "hedefRaunt");
                if (hedef > 0) toplam = hedef;
                bool rauntlu = toplam > 1;

                bool klanMaci = false;
                object km;
                if (d.TryGetValue("klanMaci", out km)) klanMaci = km is bool && (bool)km;
                string klan1 = Metin(d, "klanAd1"), klan2 = Metin(d, "klanAd2");
                bool klanli = klanMaci && klan1.Length > 0 && klan2.Length > 0;
                string takim1 = klanli ? klan1 : AnaPencere.S("Çete", "Gangsters");
                string takim2 = klanli ? klan2 : AnaPencere.S("Özel Tim", "SWAT");

                // Skor satiri: rauntlu modda raunt galibiyetleri, digerinde
                // modun kendi sayaci (DM oldurme, Karambol teslim...).
                string rauntSkor = SkorMetni(d, "skor");
                string takimSkor = SkorMetni(d, "takimSkoru");
                string skor = rauntlu ? rauntSkor : (takimSkor.Length > 0 ? takimSkor : rauntSkor);
                string rauntSatiri = rauntlu ? "Round " + raunt + "/" + toplam : "";
                long hedefSkor = Sayi(d, "hedefSkor");

                // Kendi tarafin + K/D (sunucu 12.09 gece ve sonrasi).
                long takim = Sayi(d, "takim");
                bool kdVar = d.ContainsKey("oldurme") && d.ContainsKey("olum");
                string kd = kdVar ? Sayi(d, "oldurme") + "/" + Sayi(d, "olum") : "";
                string tarafAdi = takim == 1 ? takim1 : (takim == 2 ? takim2 : "");

                var parcalar = new List<string>();
                if (klanli)
                {
                    ayrinti = AnaPencere.S("Klan Maçı ", "Clan Match ") + klan1 + " vs " + klan2;
                    if (harita.Length > 0) parcalar.Add(harita);
                    if (rauntSatiri.Length > 0) parcalar.Add(rauntSatiri);
                    if (skor.Length > 0) parcalar.Add(skor);
                }
                else
                {
                    string hm = HaritaMod(harita, mod);
                    ayrinti = hm.Length > 0 ? hm : AnaPencere.S("Maçta", "In a match");
                    if (rauntSatiri.Length > 0) parcalar.Add(rauntSatiri);
                    if (skor.Length > 0) parcalar.Add(takim1 + " " + skor + " " + takim2);
                    if (!rauntlu && hedefSkor > 0) parcalar.Add(AnaPencere.S("hedef ", "target ") + hedefSkor);
                }
                if (kd.Length > 0) parcalar.Add(kd);
                if (parcalar.Count > 0) hal = string.Join(" · ", parcalar.ToArray());

                // Tooltip'ler
                string hmt = HaritaMod(harita, mod);
                buyukMetin = "S2 Rebirth" + (hmt.Length > 0 ? " · " + hmt : "");
                string gecmis = RauntGecmisi(d, klanli ? Kisalt(takim1) : AnaPencere.S("Ç", "G"), klanli ? Kisalt(takim2) : AnaPencere.S("ÖT", "S"));
                if (gecmis.Length > 0) buyukMetin += " · " + AnaPencere.S("Rauntlar: ", "Rounds: ") + gecmis;
                if (tarafAdi.Length > 0)
                {
                    kucukMetin = tarafAdi + AnaPencere.S(" tarafında", " side");
                    if (kdVar) kucukMetin += " · " + Sayi(d, "oldurme") + AnaPencere.S(" öldürme / ", " kills / ") + Sayi(d, "olum") + AnaPencere.S(" ölüm", " deaths");
                }
                else kucukMetin = AnaPencere.S("Maçta", "In a match") + (parti != null ? " · " + kisi + "/" + kapasite : "");

                // Saat: geri sayim varsa "left", yoksa gecen sure.
                long b = Sayi(d, "baslangic");
                if (b > 0) baslangic = b / 1000;
                long gs = Sayi(d, "geriSayimBitis");
                if (gs > 0) bitis = gs / 1000;
            }
            else if (durum == "cevrimdisi")
                ayrinti = AnaPencere.S("Giriş ekranında", "At the login screen");
            else
                ayrinti = AnaPencere.S("Oynuyor", "Playing");

            var etkinlik = new Dictionary<string, object>();
            etkinlik["details"] = Kirp(ayrinti);
            if (hal != null && hal.Length > 0) etkinlik["state"] = Kirp(hal);
            if (bitis > 0)
                etkinlik["timestamps"] = new Dictionary<string, object> { { "start", baslangic }, { "end", bitis } };
            else
                etkinlik["timestamps"] = new Dictionary<string, object> { { "start", baslangic } };
            etkinlik["assets"] = new Dictionary<string, object> {
                { "large_image", "s2" }, { "large_text", Kirp(buyukMetin) },
                { "small_image", kucuk }, { "small_text", Kirp(kucukMetin ?? ayrinti) },
            };
            // party.size yalniz `state` varken cizilir; oda/mac disinda anlamsiz.
            if (parti != null && hal != null && hal.Length > 0)
                etkinlik["party"] = new Dictionary<string, object> { { "size", parti } };
            if (!string.IsNullOrEmpty(site))
                etkinlik["buttons"] = new object[] {
                    new Dictionary<string, object> { { "label", SiteEtiketi(site) }, { "url", site } },
                };
            etkinlik["instance"] = false;

            var args = new Dictionary<string, object> { { "pid", pid }, { "activity", etkinlik } };
            var cerceve = new Dictionary<string, object> {
                { "cmd", "SET_ACTIVITY" }, { "args", args }, { "nonce", Guid.NewGuid().ToString() },
            };
            return Js.Serialize(cerceve);
        }

        /// <summary>`rauntGecmisi` [1,2,0,1] -> "Ç ÖT = Ç" (0 = berabere).</summary>
        static string RauntGecmisi(Dictionary<string, object> d, string ad1, string ad2)
        {
            object v;
            if (d == null || !d.TryGetValue("rauntGecmisi", out v)) return "";
            var liste = v as object[];
            if (liste == null || liste.Length == 0) return "";
            var sb = new StringBuilder();
            foreach (var x in liste)
            {
                long t = 0;
                try { t = Convert.ToInt64(x); } catch { }
                if (sb.Length > 0) sb.Append(' ');
                sb.Append(t == 1 ? ad1 : (t == 2 ? ad2 : "="));
            }
            return sb.ToString();
        }

        static string Kisalt(string ad)
        {
            ad = (ad ?? "").Trim();
            return ad.Length > 5 ? ad.Substring(0, 5) : ad;
        }

        /// <summary>"https://s2rebirth.com/" -> "s2rebirth.com" (dugme etiketi, en cok 32).</summary>
        static string SiteEtiketi(string site)
        {
            string e = site;
            try { e = new Uri(site).Host; } catch { }
            return e.Length > 32 ? e.Substring(0, 32) : e;
        }

        static string TemizJson(int pid)
        {
            var args = new Dictionary<string, object> { { "pid", pid } };
            var cerceve = new Dictionary<string, object> {
                { "cmd", "SET_ACTIVITY" }, { "args", args }, { "nonce", Guid.NewGuid().ToString() },
            };
            return Js.Serialize(cerceve);
        }

        /// <summary>[a, b] skor dizisini "a–b" yapar; yoksa bos.</summary>
        static string SkorMetni(Dictionary<string, object> d, string anahtar)
        {
            object sk;
            if (d == null || !d.TryGetValue(anahtar, out sk)) return "";
            var liste = sk as object[];
            if (liste == null || liste.Length < 2) return "";
            return Convert.ToString(liste[0]) + "–" + Convert.ToString(liste[1]);
        }

        static string HaritaMod(string harita, string mod)
        {
            if (harita.Length > 0 && mod.Length > 0) return harita + " · " + mod;
            return harita.Length > 0 ? harita : mod;
        }

        /// <summary>Discord alanlari 128 karakter; guvenli tarafta kaliyoruz.</summary>
        static string Kirp(string s)
        {
            if (s == null) return "";
            return s.Length > 120 ? s.Substring(0, 120) : s;
        }

        // -----------------------------------------------------------------
        //  GUNLUK  (%LOCALAPPDATA%\S2Rebirth\discord-varlik.log, 200 KB tavan)
        // -----------------------------------------------------------------

        static readonly object GunlukKilidi = new object();
        static void Gunluk(string satir)
        {
            try
            {
                lock (GunlukKilidi)
                {
                    string klasor = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "S2Rebirth");
                    Directory.CreateDirectory(klasor);
                    string yol = Path.Combine(klasor, "discord-varlik.log");
                    if (File.Exists(yol) && new FileInfo(yol).Length > 200 * 1024) File.Delete(yol);
                    File.AppendAllText(yol, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + satir + "\r\n", Encoding.UTF8);
                }
            }
            catch { }
        }

        // -----------------------------------------------------------------
        //  DISCORD BORUSU
        // -----------------------------------------------------------------

        sealed class DiscordBoru
        {
            NamedPipeClientStream _p;
            IAsyncResult _bekleyen;          // yarim kalmis baslik okumasi
            readonly byte[] _baslik = new byte[8];

            public static DiscordBoru Bagla(string uygulama)
            {
                for (int n = 0; n < 10; n++)
                {
                    NamedPipeClientStream p = null;
                    try
                    {
                        p = new NamedPipeClientStream(".", "discord-ipc-" + n, PipeDirection.InOut, PipeOptions.Asynchronous);
                        p.Connect(250);
                    }
                    catch
                    {
                        if (p != null) { try { p.Dispose(); } catch { } }
                        continue;
                    }
                    var b = new DiscordBoru { _p = p };
                    try
                    {
                        b.Yaz(0, "{\"v\":1,\"client_id\":\"" + uygulama + "\"}");
                        int op;
                        string cevap = b.CerceveOku(out op, 5000);
                        if (cevap != null && op == 1 && cevap.IndexOf("READY", StringComparison.Ordinal) >= 0) return b;
                        Gunluk("el sikisma reddedildi op=" + op + " " + (cevap ?? "(yok)"));
                    }
                    catch (Exception e) { Gunluk("el sikisma: " + e.Message); }
                    b.Kapat();
                }
                return null;
            }

            public bool Gonder(string json)
            {
                try { Yaz(1, json); return true; } catch { return false; }
            }

            /// <summary>
            /// Gelen cerceveleri tuketir; ping'e pong doner. Boru kapandiysa
            /// false. Bloklamaz: baslik okumasi asenkron baslatilip bir sonraki
            /// cagrida denetleniyor.
            /// </summary>
            public bool Dinle()
            {
                try
                {
                    for (int tur = 0; tur < 4; tur++)
                    {
                        if (_bekleyen == null) _bekleyen = _p.BeginRead(_baslik, 0, 8, null, null);
                        if (!_bekleyen.IsCompleted) return true;
                        int okunan = _p.EndRead(_bekleyen);
                        _bekleyen = null;
                        if (okunan < 8) return false;   // kapandi
                        int op = BitConverter.ToInt32(_baslik, 0);
                        int uzunluk = BitConverter.ToInt32(_baslik, 4);
                        string govde = GovdeOku(uzunluk);
                        if (govde == null) return false;
                        if (op == 2) return false;                  // CLOSE
                        if (op == 3) Yaz(4, govde);                 // PING -> PONG
                    }
                    return true;
                }
                catch { return false; }
            }

            string CerceveOku(out int op, int zamanAsimiMs)
            {
                op = -1;
                var ar = _p.BeginRead(_baslik, 0, 8, null, null);
                if (!ar.AsyncWaitHandle.WaitOne(zamanAsimiMs)) { _bekleyen = ar; return null; }
                int okunan = _p.EndRead(ar);
                if (okunan < 8) return null;
                op = BitConverter.ToInt32(_baslik, 0);
                return GovdeOku(BitConverter.ToInt32(_baslik, 4));
            }

            string GovdeOku(int uzunluk)
            {
                if (uzunluk < 0 || uzunluk > 1 << 20) return null;
                var veri = new byte[uzunluk];
                int toplam = 0;
                while (toplam < uzunluk)
                {
                    int n = _p.Read(veri, toplam, uzunluk - toplam);
                    if (n <= 0) return null;
                    toplam += n;
                }
                return Encoding.UTF8.GetString(veri);
            }

            void Yaz(int op, string json)
            {
                byte[] veri = Encoding.UTF8.GetBytes(json);
                var paket = new byte[8 + veri.Length];
                BitConverter.GetBytes(op).CopyTo(paket, 0);
                BitConverter.GetBytes(veri.Length).CopyTo(paket, 4);
                veri.CopyTo(paket, 8);
                lock (this)
                {
                    _p.Write(paket, 0, paket.Length);
                    _p.Flush();
                }
            }

            public void Kapat()
            {
                try { _p.Dispose(); } catch { }
            }
        }
    }
}
