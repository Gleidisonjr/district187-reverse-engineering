// KumHavuzu.cs - Sandboxie (sanal kutu) tespiti.
//
// ---- NEDEN VAR (11-12.09.2026) -----------------------------------------
// Bir oyuncu Sandboxie ile ayni PC'de bes istemci acip kendi kukla
// hesaplarina karsi oynadi: oyunun "tek ornek" kilidi adlandirilmis bir
// nesne ve kutu onu kendi ad alanina aldigi icin ikinci istemci kilidi
// gormuyor. ApexGuard da SbieDll.dll'i surec dogarken yuklendigi icin
// "eski modul" sayiyordu. Iki tarafa da tespit kondu: ApexGuard S2-180
// (oyun icinde kovar), launcher (buradaki) daha oyunu acmadan durur.
//
// ---- IKI BAGIMSIZ SINYAL (ApexGuard ile birebir ayni) ----------------------
//  1) Bu surecin modul listesinde sbiedll.dll / sbiedllx.dll var mi.
//     Sandboxie kutudaki HER surece bunu enjekte eder; launcher da kutuda
//     aciliyorsa onda da vardir.
//  2) Kendi adimizla bir Event yaratip NtQueryObject(ObjectNameInformation)
//     ile gercek NT yolunu okuyoruz; kutu icinde yol
//     "\Sandbox\<kullanici>\<kutu>\..." onekini tasir. Kernel surucusunun
//     davranisi - DLL gizlenmis olsa da degismez.
//
// Ikisi de milisaniye altinda; acilista bir kez calisir. Yanlis pozitif
// yolu bilinmiyor - mesru bir oyuncunun launcher'i kutuda acmasi icin
// sebep yok.
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace S2Launcher
{
    internal static class KumHavuzu
    {
        [StructLayout(LayoutKind.Sequential)]
        private struct UNICODE_STRING
        {
            public ushort Length;
            public ushort MaximumLength;
            public IntPtr Buffer;
        }

        [DllImport("ntdll.dll")]
        private static extern int NtQueryObject(IntPtr handle, int infoClass, IntPtr buffer, int length, out int returnLength);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateEventW(IntPtr attrs, bool manualReset, bool initialState, string name);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        /// <summary>Kutu icindeysek aciklama doner, degilsek null.</summary>
        public static string Tespit()
        {
            string modul = ModulSinyali();
            if (modul != null) return "Sandboxie modulu yuklu: " + modul;
            string yol = NesneOneki();
            if (yol != null) return "adlandirilmis nesne kutu onekinde: " + yol;
            return null;
        }

        private static string ModulSinyali()
        {
            try
            {
                foreach (ProcessModule m in Process.GetCurrentProcess().Modules)
                {
                    string ad = (m.ModuleName ?? "").ToLowerInvariant();
                    if (ad == "sbiedll.dll" || ad == "sbiedllx.dll") return m.FileName;
                }
            }
            catch { }
            return null;
        }

        private static string NesneOneki()
        {
            IntPtr h = IntPtr.Zero;
            IntPtr buf = IntPtr.Zero;
            try
            {
                string ad = "S2LauncherSonda_" + Process.GetCurrentProcess().Id + "_" + Environment.TickCount;
                h = CreateEventW(IntPtr.Zero, false, false, ad);
                if (h == IntPtr.Zero) return null;
                const int boy = 2048;
                buf = Marshal.AllocHGlobal(boy);
                int donen;
                int st = NtQueryObject(h, 1 /* ObjectNameInformation */, buf, boy, out donen);
                if (st != 0) return null;
                UNICODE_STRING us = (UNICODE_STRING)Marshal.PtrToStructure(buf, typeof(UNICODE_STRING));
                if (us.Buffer == IntPtr.Zero || us.Length == 0) return null;
                string yol = Marshal.PtrToStringUni(us.Buffer, us.Length / 2);
                if (yol.ToLowerInvariant().Contains("\\sandbox\\")) return yol;
                return null;
            }
            catch { return null; }
            finally
            {
                if (buf != IntPtr.Zero) Marshal.FreeHGlobal(buf);
                if (h != IntPtr.Zero) CloseHandle(h);
            }
        }
    }
}
