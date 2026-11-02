// =====================================================================
//  ⛔ 28.08.2026 - BU ORNEKLEYICI OYUNU TAKIYORDU (K-391)
// =====================================================================
//
//  Belirti: "akicilik gidiyor, karakterler isinlaniyor". Tani ozelligi
//  (yerel gunluk + cikista upload) kapatilinca DUZELDI. Olcum:
//
//    Refresh() + WorkingSet64            6,67 ms
//    Refresh() + Threads.Count           6,50 ms
//    Refresh() + hepsi (bu dongu)        7,34 ms   <- 250 ms'de BIR
//    TotalProcessorTime                  0,03 ms
//    GetUdpIPv4Statistics                0,02 ms
//    nic.GetIPv4Statistics               0,10 ms
//
//  SEBEP: .NET'te `Process.WorkingSet64` ve `Process.Threads`, `Refresh()`
//  sonrasi `NtQuerySystemInformation(SystemProcessInformation)` cagiriyor -
//  yani MAKINEDEKI TUM sureclerin ve is parcaciklarinin anlik goruntusu.
//  Ham cagri olculdu:
//
//    NtQuerySystemInformation(5): ort 8,58 ms, max 13,36 ms,
//    tampon 1.013.984 BAYT  (421 surec / ~8.900 is parcacigi)
//
//  Bunu saniyede DORT kez yapiyorduk, mac boyunca. 1 MB'lik cekirdek
//  yurüyusu surec listesi kilidini tutuyor; oyunun 5-7 ms'lik karesinin
//  icine dusunce kare suresi katlaniyor. Duzenli 4 Hz'lik takilma =
//  tarif edilen belirtinin ta kendisi. Oyuncunun acik surec sayisi
//  arttikca maliyet BUYUYOR - bu yuzden herkeste ayni siddette degil.
//
//  ⚠ "hafif, ayri surecte" notu YANLISTI: ayri surecte olmasi kilidi
//  paylasmasini engellemiyor.
//
//  UCUZ ALTERNATIF (olculdu: 0,046 ms - 145 kat ucuz), sistem geneli
//  goruntu ALMADAN, zaten acik olan surec tutamagi uzerinden:
//      psapi!GetProcessMemoryInfo   -> WorkingSetSize
//      kernel32!GetProcessTimes     -> kernel+user sure
//  Is parcacigi sayisi gerekiyorsa 250 ms degil ~10 sn'de bir alinmali.
//
// =====================================================================
// =====================================================================
//  AG IZI - oyun boyunca ag sayaclarini ornekler
// =====================================================================
//
//  ---- NEDEN VAR: OLCULEN DURUM ---------------------------------------
//
//  Sikayet: "Pingler yesil, mermi aninda olduruyor, AMA karakterler
//  isinlaniyor." 26.08.2026'da sunucu tarafi bastan asagi olculdu ve
//  su adaylarin HEPSI ELENDI:
//
//    * sunucu tiki      30 Hz duzenli (p50=33 ms, p90=34)
//    * bant siniri      66 kbit/sn kullaniliyor, tavan 256 kbit/sn (%26)
//    * istemci yukari akisi  HAREKETLI orneklerde %1,12 bosluk, adim 29-83 birim
//    * bosluklar es zamanli mi?  p=0,878 -> BAGIMSIZ, ortak sebep yok
//    * kestirim kapali mi?  GameClient acilista "Prediction" = 1.0 SET EDIYOR
//                           (sub_10021070 ve sub_10022040, ikisi de `fld1`)
//    * MaxExtrapolateTime   0,5 sn - 33 ms'lik akista hic dolmuyor
//    * istemci kare takilmasi  ELENDI: takilsaydi DUNYA da donardi,
//                           oysa dunya akici, yalniz karakterler zipliyor
//
//  Geriye TEK bilinmeyen kaldi: SUNUCUNUN GONDERDIGI 30 Hz, OYUNCUNUN
//  MAKINESINE GERCEKTEN 30 Hz OLARAK VARIYOR MU? Sunucudaki yakalama
//  yolun oyuncuya kadarki kismini goremiyor. Bu dosya o boslugu kapatiyor.
//
//  ---- NE OLCUYOR ------------------------------------------------------
//
//  250 ms'de bir, YALNIZCA ISLETIM SISTEMI SAYACLARI okunuyor:
//
//    UDP  : alinan datagram, atilan, hatali        (IPGlobalProperties)
//    NIC  : alinan paket, ATILAN paket, hatali     (NetworkInterface)
//    Oyun : calisma kumesi, CPU suresi, is parcacigi (Process)
//
//  Ham sayaclar yaziliyor, fark DEGIL: bir ornek atlansa bile aradaki
//  fark hesaplanabilir kalsin diye.
//
//  Cozumleme sorusu: oyun sirasinda alinan paket hizi 30/sn civarinda
//  SABIT mi, yoksa donem donem cokuyor mu? Cokuyorsa sebep AGDA; sabit
//  kaliyorsa sebep istemcinin CIZIM tarafinda ve oraya bakilir.
//
//  ---- ⚠ SAYACLAR SISTEM GENELI - HANGISINE GUVENILIR -----------------
//
//  Windows UDP icin SUREC BASINA sayac vermiyor (`GetPerTcpConnection
//  EStats` yalnizca TCP). Yani `udpAlinan` makinedeki TUM UDP trafigini
//  sayiyor - tarayici, Discord, Windows'un kendisi de icinde.
//  Olculdu (gelistirme kutusu, oyun KAPALIYKEN): ~76 datagram/sn taban
//  gurultu. Oyunun katkisi ~30/sn, yani sinyal/gurultu iyi degil.
//
//  Bu yuzden ONEM SIRASI:
//
//    1. nicAtilan / udpAtilan / udpHatali   ← TEMIZ SINYAL
//       Bunlar bos zamanda SABIT durur. Oyun sirasinda ARTIYORSA
//       paketler oyuncunun kartinda/yiginda dusuyor demektir. Tek
//       basina kanit sayilir.
//    2. udpAlinan / nicPaket hizi           ← GURULTULU
//       Yalniz SURDURULEN bir cokus anlamli (orn. 30 sn boyunca yariya
//       inmesi). Tek tek dalgalanma yorumlanmaz.
//
//  Iz oyun sureci dogar dogmaz basliyor; oyunun maca girmesi 20-30 sn
//  suruyor. O ilk saniyeler MAKINENIN TABAN GURULTUSU olarak kullanilir -
//  cozumlemede ondan cikarilir.
//
//  ---- ⛔ OYUNA HICBIR SEY YAPMIYOR ------------------------------------
//
//  Enjeksiyon yok, kanca yok, oyunun belleğine dokunulmuyor, tek bayt
//  yazilmiyor. Yalnizca isletim sisteminin kendi sayaclari okunuyor -
//  Gorev Yoneticisi'nin yaptigi seyin aynisi.
//
//  ⚠ WMI ve PerformanceCounter BILEREK KULLANILMIYOR. Ikisi de bozuk
//    kurulumlarda saniyelerce asili kalabiliyor. `System.Net.
//    NetworkInformation` cagrilari GetIfEntry/GetUdpStatistics uzerine
//    ince sarmalayici - mikrosaniye mertebesinde.
//
//  ⚠ ARKA PLAN IS PARCACIGI (IsBackground = true): launcher kapanirken
//    bu is parcacigi cikisi ENGELLEYEMEZ. Kendisi patlasa bile yalnizca
//    ornekleme durur; oyun ve launcher etkilenmez, paketin geri kalani
//    normal toplanir.
//
//  ⚠ ADAPTOR BIR KEZ SECILIYOR: makinede 20 sanal adaptor olabilir
//    (VPN, Hyper-V, VirtualBox). Her orneklemede hepsini gezmek pahali
//    olurdu; baslangicta EN COK TRAFIGI olan secilip ona bakiliyor.
//
//  ---- BOYUT -----------------------------------------------------------
//
//  Satir ~70 bayt, saniyede 4 satir -> saatte ~1 MB. Tavan 3 MB'ta
//  ornekleme DURUYOR (paket tavani 90 MB, gunluk tavani 8 MB - yani
//  bu dosya pakette gurultu bile sayilmaz).
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace S2Launcher
{
    /// <summary>Oyun boyunca ag sayaclarini ornekleyen kara kutu ucu.</summary>
    public sealed class AgIzi
    {
        /// <summary>Ornekleme araligi. 250 ms: 30 Hz akista kova basina ~7,5
        /// paket dusuyor, yani hizin YARIYA inmesi bile ayirt edilebiliyor.</summary>
        const int ARALIK_MS = 250;

        /// <summary>Bu boyuta gelince ornekleme durur (yaklasik 3 saat).</summary>
        const long TAVAN = 3L * 1024 * 1024;

        /// <summary>
        /// Is parcacigi sayisi kac ornekte bir okunacak. 40 x 250 ms = 10 sn.
        ///
        /// Bunun ONE CIKAN sebebi maliyet: `Process.Threads` sistem geneli
        /// anlik goruntu istiyor (asagidaki K-391 blogu). RSS ve CPU artik
        /// ucuz yoldan okunuyor ama is parcacigi sayisinin ucuz karsiligi
        /// yok - o yuzden seyreltildi. Sayi zaten yavas degisen bir olcut.
        /// </summary>
        const int IP_SAYIM_HER = 40;

        // ---- UCUZ SUREC SAYAClARI (K-391 duzeltmesi, 31.08.2026) --------
        //
        // Bu iki cagri ZATEN ACIK olan surec tutamagi uzerinden calisir;
        // sistem geneli surec listesi YURUNMEZ. Olculen fark:
        //     Process.Refresh()+WorkingSet64+Threads.Count   7,34 ms
        //     GetProcessMemoryInfo + GetProcessTimes         0,046 ms   (145x)
        //
        // ⚠ Basarisiz olurlarsa deger -1 kalir; dosya bicimi degismez.

        [StructLayout(LayoutKind.Sequential)]
        struct SUREC_BELLEK
        {
            public uint cb;
            public uint SayfaHatasi;
            public IntPtr TepeCalismaKumesi;
            public IntPtr CalismaKumesi;
            public IntPtr TepeSayfaliHavuz;
            public IntPtr SayfaliHavuz;
            public IntPtr TepeSayfasizHavuz;
            public IntPtr SayfasizHavuz;
            public IntPtr SayfaDosyasi;
            public IntPtr TepeSayfaDosyasi;
        }

        [DllImport("psapi.dll", SetLastError = true)]
        static extern bool GetProcessMemoryInfo(IntPtr surec, out SUREC_BELLEK sayac, uint boy);

        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool GetProcessTimes(IntPtr surec, out long olusma, out long cikis,
                                           out long cekirdek, out long kullanici);

        readonly string _dosya;
        readonly Process _oyun;
        Thread _isParcacigi;
        volatile bool _dur;

        /// <summary>Son okunan is parcacigi sayisi - IP_SAYIM_HER ornekte bir tazelenir.</summary>
        int _sonIp = -1;

        AgIzi(string dosya, Process oyun)
        {
            _dosya = dosya;
            _oyun = oyun;
        }

        /// <summary>
        /// Izi baslatir. HICBIR KOSULDA FIRLATMAZ - cagiran tarafta
        /// try/catch gerekmesin diye. Basarisiz olursa null doner ve
        /// oturum ag izi olmadan devam eder.
        /// </summary>
        public static AgIzi Basla(string klasor, Process oyun)
        {
            try
            {
                if (string.IsNullOrEmpty(klasor)) return null;
                Directory.CreateDirectory(klasor);
                var iz = new AgIzi(Path.Combine(klasor, "ag-izi.csv"), oyun);
                iz._isParcacigi = new Thread(iz.Dongu);
                iz._isParcacigi.IsBackground = true;   // cikisi asla engelleme
                iz._isParcacigi.Priority = ThreadPriority.BelowNormal;
                iz._isParcacigi.Start();
                return iz;
            }
            catch { return null; }
        }

        /// <summary>Ornellemeyi durdurur ve dosyayi kapatir. Firlatmaz.</summary>
        public void Bitir()
        {
            try
            {
                _dur = true;
                if (_isParcacigi != null) _isParcacigi.Join(1000);
            }
            catch { }
        }

        /// <summary>
        /// EN COK TRAFIGI olan calisan adaptor. Sanal adaptorler (VPN,
        /// Hyper-V, VirtualBox) genelde bos durur; gercek kart bayt
        /// sayacindan ayirt ediliyor. Ad EZBERLENMIYOR - marka/surucu
        /// adina bagli bir suzgec makineye gore tutmazdi.
        /// </summary>
        static NetworkInterface AdaptorSec()
        {
            NetworkInterface secilen = null;
            long enCok = -1;
            foreach (NetworkInterface n in NetworkInterface.GetAllNetworkInterfaces())
            {
                try
                {
                    if (n.OperationalStatus != OperationalStatus.Up) continue;
                    if (n.NetworkInterfaceType == NetworkInterfaceType.Loopback) continue;
                    long b = n.GetIPv4Statistics().BytesReceived;
                    if (b > enCok) { enCok = b; secilen = n; }
                }
                catch { }
            }
            return secilen;
        }

        void Dongu()
        {
            StreamWriter yaz = null;
            try
            {
                NetworkInterface nic = AdaptorSec();
                yaz = new StreamWriter(_dosya, false, new UTF8Encoding(false));
                yaz.WriteLine("# S2 ag izi - 250 ms araliklarla HAM sayaclar (fark degil)");
                yaz.WriteLine("# adaptor=" + (nic != null ? nic.Description : "(bulunamadi)"));
                yaz.WriteLine("ms,udpAlinan,udpAtilan,udpHatali,nicPaket,nicAtilan,nicHatali,rssMb,cpuMs,isParcacigi");
                yaz.Flush();

                var saat = Stopwatch.StartNew();
                long yazilan = 0;
                long ornek = 0;
                var sb = new StringBuilder(96);

                while (!_dur)
                {
                    // Oyun kapandiysa ornekleme anlamsiz.
                    try { if (_oyun != null && _oyun.HasExited) break; } catch { }

                    long udpAl = -1, udpAt = -1, udpHt = -1;
                    long nicPk = -1, nicAt = -1, nicHt = -1;
                    long rss = -1, cpu = -1; int ip = -1;

                    try
                    {
                        UdpStatistics u = System.Net.NetworkInformation.IPGlobalProperties
                            .GetIPGlobalProperties().GetUdpIPv4Statistics();
                        udpAl = u.DatagramsReceived;
                        udpAt = u.IncomingDatagramsDiscarded;
                        udpHt = u.IncomingDatagramsWithErrors;
                    }
                    catch { }

                    try
                    {
                        if (nic != null)
                        {
                            IPv4InterfaceStatistics st = nic.GetIPv4Statistics();
                            nicPk = st.UnicastPacketsReceived;
                            nicAt = st.IncomingPacketsDiscarded;
                            nicHt = st.IncomingPacketsWithErrors;
                        }
                    }
                    catch { }

                    // ---- K-391 DUZELTMESI: sistem geneli goruntu ALINMIYOR ----
                    // Eski hali her 250 ms araliginda `_oyun.Refresh()` +
                    // `WorkingSet64` + `Threads.Count` cagiriyordu; ucu de
                    // NtQuerySystemInformation(SystemProcessInformation) demek,
                    // yani makinedeki TUM sureclerin 1 MB kadar anlik goruntusu
                    // (ort 8,58 ms). Saniyede dort kez = duzenli 4 Hz takilma.
                    try
                    {
                        if (_oyun != null && !_oyun.HasExited)
                        {
                            IntPtr h = _oyun.Handle;   // Start ile gelen tutamak

                            SUREC_BELLEK bellek;
                            if (GetProcessMemoryInfo(h, out bellek, (uint)Marshal.SizeOf(typeof(SUREC_BELLEK))))
                            {
                                rss = (long)((ulong)bellek.CalismaKumesi / (1024 * 1024));
                            }

                            long ol, ck, cekirdek, kullanici;
                            if (GetProcessTimes(h, out ol, out ck, out cekirdek, out kullanici))
                            {
                                // FILETIME 100 ns birimli -> ms
                                cpu = (cekirdek + kullanici) / 10000L;
                            }

                            // Is parcacigi sayisinin ucuz karsiligi yok; 10 saniyede bir.
                            if (ornek % IP_SAYIM_HER == 0)
                            {
                                _oyun.Refresh();
                                _sonIp = _oyun.Threads.Count;
                            }
                            ip = _sonIp;
                        }
                    }
                    catch { }

                    sb.Length = 0;
                    sb.Append(saat.ElapsedMilliseconds).Append(',')
                      .Append(udpAl).Append(',').Append(udpAt).Append(',').Append(udpHt).Append(',')
                      .Append(nicPk).Append(',').Append(nicAt).Append(',').Append(nicHt).Append(',')
                      .Append(rss).Append(',').Append(cpu).Append(',').Append(ip);
                    string satir = sb.ToString();
                    yaz.WriteLine(satir);
                    yazilan += satir.Length + 2;

                    // ⚠ Her satirda Flush YOK: oyun sirasinda saniyede dort
                    //   disk yazimi gereksiz. Saniyede bir yetiyor; cokmede
                    //   en fazla son bir saniye kaybolur.
                    if ((saat.ElapsedMilliseconds / ARALIK_MS) % 4 == 0) yaz.Flush();

                    if (yazilan > TAVAN)
                    {
                        yaz.WriteLine("# TAVAN - ornekleme durdu");
                        break;
                    }

                    ornek += 1;
                    Thread.Sleep(ARALIK_MS);
                }
            }
            catch { }
            finally
            {
                try { if (yaz != null) { yaz.Flush(); yaz.Dispose(); } } catch { }
            }
        }
    }
}
