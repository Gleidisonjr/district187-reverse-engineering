// District 187: Sin Streets - Native LithTech Jupiter EX Dedicated Server Host (x86)
// Loads authentic Engine_Server.dll + Game\GameServer.dll and hosts a .World00p map on UDP 27888.

#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cwchar>
#include <cstdarg>
#include <intrin.h>
#pragma comment(lib, "ws2_32.lib")

// LithTech Jupiter EX ABI structures (verified empirically against Engine_Server.dll)
#define SI_VERSION 2

struct LTGUID {
    uint32_t a;
    uint16_t b;
    uint16_t c;
    uint8_t  d[8];
};

typedef uint32_t LTRESULT;
typedef void* HNETSERVICE;

struct NetService {
    HNETSERVICE m_handle;
    uint32_t    m_dwFlags;
    LTGUID      m_guidService;
    char        m_sName[128]; // offset +0x18 .. +0x97
    NetService* m_pNext;      // verified at +0x98 in FreeServiceList (0x1004a9a2)
};

// Verified against CUDPDriver::HostSession (0x1007bb51), UTF-16LE strings:
// +0x0000: uint16_t m_Port (0 defaults to 0x6cf0 = 27888)
// +0x0004: wchar_t  m_sBindAddr[0x22] (0x44 bytes)
// +0x0048: uint32_t m_dwMaxConnections
// +0x004C: wchar_t  m_sName[0x1000] (0x2000 bytes)
// +0x204C: uint8_t  m_bHasPassword
// +0x204D: uint8_t  m_bUsePassword
#pragma pack(push, 1)
struct NetHost {
    uint16_t m_Port;
    uint16_t m_Pad;
    wchar_t  m_sBindAddr[0x22];
    uint32_t m_dwMaxConnections;
    wchar_t  m_sName[0x1000];
    uint8_t  m_bHasPassword;
    uint8_t  m_bUsePassword;
    uint8_t  m_Reserved[0x32];
};
#pragma pack(pop)

// Verified against CLTServerInterface::StartWorld (slot 10, 0x10062259):
// +0x0000: int m_Type (3 = STARTGAME_HOST)
// +0x0004: char m_WorldName[100]
// +0x0068: NetHost / HostInfo + extra game request data
// +0x2188: void* m_pGameInfo
// +0x218C: uint32_t m_GameInfoLen
#pragma pack(push, 1)
struct VC10EmptyString {
    char     buf[16]; // zero
    uint32_t size;    // 0
    uint32_t res;     // 15 (0x0F -> SSO inline, safe across VC14->VC10)
    uint32_t pad;     // 0
}; // sizeof == 0x1C (28 bytes)
static_assert(sizeof(VC10EmptyString) == 0x1C, "VC10EmptyString must be 0x1C");

struct ServerGameOptions {
    VC10EmptyString s[6];        // +0x00 .. +0xA7 (6 x 0x1C = 0xA8)
    uint32_t        fieldA8;     // +0xA8
    uint32_t        status;      // +0xAC (written by OnServerInitialized at 0x100568c3)
    uint8_t         tail[0x150]; // safe zeroed margin
};

struct StartGameRequest {
    int32_t  m_Type;
    char     m_WorldName[100];
    uint8_t  m_Payload[0x2188 - 0x68];
    void*    m_pGameInfo;
    uint32_t m_GameInfoLen;
    uint8_t  m_Tail[64];
};
#pragma pack(pop)

static FILE* g_LogFile = nullptr;

static void LogLine(const char* fmt, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    printf("%s", buf);
    fflush(stdout);
    if (g_LogFile) {
        fprintf(g_LogFile, "%s", buf);
        fflush(g_LogFile);
    }
}

typedef LTRESULT (__cdecl* KickClientFn)(void* hClient);
static HMODULE g_hGameServer = nullptr;
static KickClientFn g_OrigKickClient = nullptr;

// Hook CGameServerShell::OnClientEnterWorld (vtable slot 5, RVA 0x53490) to capture CPlayerObj*
// and set m_bClientLoaded (+0x934) = 1 & m_bReadyToRespawn (+0x935) = 1 so CPlayerObj::Update
// natively invokes CPlayerObj::Respawn() (Teleport + HP=100 + AddDefaultWeapons + MID 0x67 PS_ALIVE).
typedef void* (__thiscall* OnClientEnterWorldFn)(void* pShell, void* hClient);
static OnClientEnterWorldFn g_OrigOnClientEnterWorld = nullptr;
static void* g_LastPlayerObj = nullptr;
static int g_RespawnDelayTicks = -1;

static void* __fastcall HookedOnClientEnterWorld(void* pShell, void* /*edx*/, void* hClient) {
    void* pPlayer = g_OrigOnClientEnterWorld ? g_OrigOnClientEnterWorld(pShell, hClient) : nullptr;
    LogLine("[HOOK] OnClientEnterWorld(hClient=%p) -> CPlayerObj=%p\n", hClient, pPlayer);
    if (pPlayer) {
        g_LastPlayerObj = pPlayer;
        g_RespawnDelayTicks = 90; // ~1.5s after world entry so client finishes InWorld handshake
    }
    return pPlayer;
}

// GameServer.dll RVA 0x5FA20 signature (verified at 0x100960AF..0x100960C5):
// void __cdecl GameServerLog(void* pLogger, const char* fmt, ...)
static void __cdecl HookedGameServerLog(void* pLogger, const char* fmt, ...) {
    (void)pLogger;
    if (!fmt || !fmt[0]) return;
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    void** pRet = (void**)_AddressOfReturnAddress();
    uintptr_t rva = (g_hGameServer && pRet) ? ((uintptr_t)pRet[0] - (uintptr_t)g_hGameServer) : 0;
    if (rva == 0x960C0 && pRet) {
        // Called from 0x10096060 (eClientConnectionState_Error): pRet[9] is caller retAddr, pRet[12] is reason string
        uintptr_t callerRva = (uintptr_t)pRet[9] - (uintptr_t)g_hGameServer;
        const char* reason = (const char*)pRet[12];
        LogLine("[GameServer] %s (caller RVA=0x%X, reason='%s')\n",
                buf, (unsigned)callerRva, (reason && !IsBadStringPtrA(reason, 256)) ? reason : "");
    } else {
        LogLine("[GameServer][RVA=0x%X] %s\n", (unsigned)rva, buf);
    }
}

static LTRESULT __cdecl HookedKickClient(void* hClient) {
    void* retAddr = _ReturnAddress();
    uintptr_t rva = g_hGameServer ? ((uintptr_t)retAddr - (uintptr_t)g_hGameServer) : 0;
    LogLine("[HOOK] ILTServer::KickClient(hClient=%p) called from abs=%p (GameServer RVA=0x%X)\n",
            hClient, retAddr, (unsigned)rva);
    return g_OrigKickClient ? g_OrigKickClient(hClient) : 0;
}

// Engine_Server.dll RVA 0x5DD7D: void __cdecl sm_WriteModelFiles(LTObject* pObj, CPacket_Write* pPacket)
// Prologue is 9 bytes: 55 8B EC 81 EC 0C 01 00 00 (push ebp; mov ebp, esp; sub esp, 0x10c)
typedef void (__cdecl* WriteModelFilesFn)(void* pObj, void* pPacket);
static WriteModelFilesFn g_OrigWriteModelFiles = nullptr;
static void* g_LastValidModel = nullptr;
static uint8_t* g_WriteModelTrampoline = nullptr;

static void __cdecl HookedWriteModelFiles(void* pObj, void* pPacket) {
    if (pObj) {
        uint16_t objId = *(uint16_t*)((uint8_t*)pObj + 0x66);
        void** ppModel = (void**)((uint8_t*)pObj + 0x110);
        if (*ppModel) {
            const char* fname = *(const char**)(*ppModel);
            g_LastValidModel = *ppModel;
            LogLine("[ModelSync] objId=%u model='%s'\n", (unsigned)objId,
                    (fname && !IsBadStringPtrA(fname, 256)) ? fname : "<bad>");
        } else {
            LogLine("[ModelSync][WARN] objId=%u has NULL m_pModel! fallback=%p\n",
                    (unsigned)objId, g_LastValidModel);
            if (g_LastValidModel) {
                *ppModel = g_LastValidModel;
                g_OrigWriteModelFiles(pObj, pPacket);
                *ppModel = nullptr;
                return;
            }
        }
    }
    g_OrigWriteModelFiles(pObj, pPacket);
}

static void InstallEngineHooks(HMODULE hEngine) {
    if (!hEngine) return;
    uint8_t* fn = (uint8_t*)hEngine + 0x5DD7D;
    // Verify expected 9-byte prologue
    static const uint8_t expected[9] = { 0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x0C, 0x01, 0x00, 0x00 };
    if (memcmp(fn, expected, 9) != 0) {
        LogLine("[-] sm_WriteModelFiles prologue mismatch at %p\n", (void*)fn);
        return;
    }
    g_WriteModelTrampoline = (uint8_t*)VirtualAlloc(nullptr, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!g_WriteModelTrampoline) return;
    memcpy(g_WriteModelTrampoline, fn, 9);
    g_WriteModelTrampoline[9] = 0xE9;
    int32_t backRel = (int32_t)((fn + 9) - (g_WriteModelTrampoline + 14));
    memcpy(g_WriteModelTrampoline + 10, &backRel, 4);
    g_OrigWriteModelFiles = (WriteModelFilesFn)g_WriteModelTrampoline;

    DWORD oldProt = 0;
    if (VirtualProtect(fn, 9, PAGE_EXECUTE_READWRITE, &oldProt)) {
        fn[0] = 0xE9;
        int32_t rel = (int32_t)((uint8_t*)&HookedWriteModelFiles - (fn + 5));
        memcpy(fn + 1, &rel, 4);
        memset(fn + 5, 0x90, 4);
        VirtualProtect(fn, 9, oldProt, &oldProt);
        FlushInstructionCache(GetCurrentProcess(), fn, 9);
        LogLine("[+] Installed sm_WriteModelFiles hook at %p (RVA 0x5DD7D)\n", (void*)fn);
    }
}

static void InstallGameServerLogHook(HMODULE hGS) {
    if (!hGS) return;
    g_hGameServer = hGS;
    // GameServer.dll RVA 0x5FA20 is a stripped Release-build 1-byte `ret` with 15 bytes of 0xCC padding
    uint8_t* fn = (uint8_t*)hGS + 0x5FA20;
    if (fn[0] == 0xC3 && fn[1] == 0xCC) {
        DWORD oldProt = 0;
        if (VirtualProtect(fn, 5, PAGE_EXECUTE_READWRITE, &oldProt)) {
            int32_t rel = (int32_t)((uint8_t*)&HookedGameServerLog - (fn + 5));
            fn[0] = 0xE9;
            memcpy(fn + 1, &rel, 4);
            VirtualProtect(fn, 5, oldProt, &oldProt);
            FlushInstructionCache(GetCurrentProcess(), fn, 5);
            LogLine("[+] Installed GameServer.dll log hook at %p (RVA 0x5FA20)\n", (void*)fn);
        }
    }
    // Hook g_pLTServer->KickClient (+0x54) via GameServer.dll's g_pLTServer global (RVA 0x1E5AA8)
    uint8_t* pLTServer = *(uint8_t**)((uint8_t*)hGS + 0x1E5AA8);
    if (pLTServer) {
        KickClientFn* pSlot = (KickClientFn*)(pLTServer + 0x54);
        g_OrigKickClient = *pSlot;
        DWORD oldProt = 0;
        if (VirtualProtect(pSlot, sizeof(void*), PAGE_READWRITE, &oldProt)) {
            *pSlot = &HookedKickClient;
            VirtualProtect(pSlot, sizeof(void*), oldProt, &oldProt);
            LogLine("[+] Installed KickClient hook at %p (orig=%p)\n", (void*)pSlot, (void*)g_OrigKickClient);
        }
    }
}

// ServerAppHandler callback interface (LithTech Jupiter EX - no virtual destructor in slot 0!)
// Verified against Engine_Server.dll dsi_ConsolePrint (0x10087502: call [vt+4]):
//   [0] (+0x00) ShellMessageFn(void* pMsg)
//   [1] (+0x04) ConsoleOutputFn(const char* pMsg)
//   [2] (+0x08) OutOfMemory()
//   [3] (+0x0C) ProcessPacket(void* pMsg, uint8_t senderAddr[4], uint16_t senderPort)
class ServerAppHandler {
public:
    virtual LTRESULT ShellMessageFn(void* pMsg) {
        (void)pMsg;
        return 0;
    }
    virtual LTRESULT ConsoleOutputFn(const char* pMsg) {
        if (pMsg) LogLine("[Engine] %s\n", pMsg);
        return 0;
    }
    virtual LTRESULT OutOfMemory() {
        LogLine("[Engine][ERR] Out of memory!\n");
        return 0;
    }
    virtual LTRESULT ProcessPacket(void* pMsg, uint8_t senderAddr[4], uint16_t senderPort) {
        LogLine("[Engine][PKT] Unconnected packet from %u.%u.%u.%u:%u\n",
                senderAddr[0], senderAddr[1], senderAddr[2], senderAddr[3], (unsigned)senderPort);
        (void)pMsg;
        return 0;
    }
};

// Exact 28-slot vtable verified from Engine_Server.dll (0x10158bcc)
class ServerInterface {
public:
    virtual LTRESULT SetAppHandler(ServerAppHandler* pHandler) = 0;                         // [ 0] ret 4
    virtual bool     ParseCommandLine(int argc, const char** argv) = 0;                     // [ 1] ret 8
    virtual LTRESULT LoadConfigFile(const char* pFilename) = 0;                             // [ 2] ret 4
    virtual LTRESULT SaveConfigFile(const char* pFilename) = 0;                             // [ 3] ret 4
    virtual LTRESULT SendToServerShell(void* pMsg) = 0;                                     // [ 4] ret 4
    virtual bool     AddResources(const char** pResources, uint32_t nResources) = 0;        // [ 5] ret 8
    virtual bool     SetGameInfo(void* pData, uint32_t dataLen) = 0;                        // [ 6] ret 8
    virtual bool     LoadBinaries() = 0;                                                    // [ 7] ret 0
    virtual void*    Slot08(void* a) = 0;                                                   // [ 8] ret 4
    virtual void     Slot09(void* a) = 0;                                                   // [ 9] ret 4
    virtual bool     StartWorld(StartGameRequest* pRequest) = 0;                            // [10] ret 4
    virtual int      GetNumClients() = 0;                                                   // [11] ret 0
    virtual bool     Slot12(void* a, void* b, void* c) = 0;                                 // [12] ret 0xc
    virtual bool     Slot13(void* a, void* b, void* c) = 0;                                 // [13] ret 0xc
    virtual bool     Slot14(void* a, void* b) = 0;                                          // [14] ret 8
    virtual bool     Slot15(void* a) = 0;                                                   // [15] ret 4
    virtual bool     GetClientPing(uint32_t nClientId, float& ping) = 0;                    // [16] ret 8
    virtual bool     GetClientAddr(uint32_t nClientId, uint8_t pAddr[4], uint16_t* pPort) = 0; // [17] ret 0xc
    virtual bool     Slot18(void* a, void* b) = 0;                                          // [18] ret 8
    virtual bool     Update(long flags) = 0;                                                // [19] ret 4
    virtual bool     InitNetworking(const char* sDrivers, uint32_t dwFlags) = 0;            // [20] ret 8
    virtual bool     GetServiceList(NetService*& pListHead) = 0;                            // [21] ret 4
    virtual bool     FreeServiceList(NetService* pListHead) = 0;                            // [22] ret 4
    virtual bool     SelectService(HNETSERVICE hNetService) = 0;                            // [23] ret 4
    virtual bool     Slot24(void* a) = 0;                                                   // [24] ret 4 (stub +0x38)
    virtual bool     HostGame(NetHost* pHost) = 0;                                          // [25] ret 4 (CUDPDriver::HostSession +0x30)
    virtual bool     GetTcpIpAddress(char* sAddress, uint32_t dwBufferSize, uint16_t& hostPort) = 0; // [26] ret 0xc
    virtual LTRESULT SendTo(const void* pData, uint32_t len, const char* sAddr, uint32_t port) = 0;  // [27] ret 0xc
};

typedef int  (__cdecl* CreateServerFn)(int version, const LTGUID& appGuid, ServerInterface** ppServer);
typedef void (__cdecl* DeleteServerFn)();

static volatile bool g_Running = true;

static BOOL WINAPI ConsoleCtrlHandler(DWORD ctrlType) {
    if (ctrlType == CTRL_C_EVENT || ctrlType == CTRL_BREAK_EVENT || ctrlType == CTRL_CLOSE_EVENT) {
        g_Running = false;
        return TRUE;
    }
    return FALSE;
}

int main(int argc, char** argv) {
    const char* worldName = "Worlds\\Arrival.World00p";
    uint16_t port = 27888;
    int maxSeconds = 0; // 0 = run until Ctrl+C

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--world") == 0 && i + 1 < argc) {
            worldName = argv[++i];
        } else if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
            port = (uint16_t)atoi(argv[++i]);
        } else if (strcmp(argv[i], "--timeout") == 0 && i + 1 < argc) {
            maxSeconds = atoi(argv[++i]);
        }
    }

    SetConsoleCtrlHandler(ConsoleCtrlHandler, TRUE);
    g_LogFile = fopen("..\\traffic\\server_host.log", "w");

    LogLine("=====================================================================\n");
    LogLine("  District 187: Sin Streets - Native LithTech Dedicated Server Host\n");
    LogLine("  Target World: %s | UDP Port: %u\n", worldName, (unsigned)port);
    LogLine("=====================================================================\n");

    HMODULE hEngine = LoadLibraryA("Engine_Server.dll");
    if (!hEngine) {
        printf("[-] Failed to load Engine_Server.dll (GetLastError=%lu)\n", GetLastError());
        return 1;
    }
    printf("[+] Loaded Engine_Server.dll at %p\n", (void*)hEngine);

    auto pCreateServer = (CreateServerFn)GetProcAddress(hEngine, "CreateServer");
    auto pDeleteServer = (DeleteServerFn)GetProcAddress(hEngine, "DeleteServer");
    if (!pCreateServer || !pDeleteServer) {
        printf("[-] Missing CreateServer/DeleteServer exports\n");
        FreeLibrary(hEngine);
        return 2;
    }

    // Authentic District 187 / S2 Online LTGUID (extracted from TheRaw.exe CNetMgr+0x28):
    // {DF560590-D918-4A51-9CB1-38EBBE3879AD}
    LTGUID appGuid = { 0xDF560590, 0xD918, 0x4A51, { 0x9C, 0xB1, 0x38, 0xEB, 0xBE, 0x38, 0x79, 0xAD } };
    ServerInterface* pServer = nullptr;
    int status = pCreateServer(SI_VERSION, appGuid, &pServer);
    printf("[+] CreateServer(SI_VERSION=%d) -> status=%d, pServer=%p\n", SI_VERSION, status, (void*)pServer);
    fflush(stdout);
    if (status != 0 || !pServer) {
        printf("[-] CreateServer failed!\n");
        FreeLibrary(hEngine);
        return 3;
    }

    ServerAppHandler appHandler;
    LTRESULT res = pServer->SetAppHandler(&appHandler);
    printf("[+] SetAppHandler -> %u\n", res);
    fflush(stdout);

    // Enable Engine_Server.dll NetDebugOut (+0x17EDF4 / +0x17EDF0) and CUDPDriver::Disconnect log (+0x17EDC8)
    *(int32_t*)((uint8_t*)hEngine + 0x17EDF4) = 5;
    *(int32_t*)((uint8_t*)hEngine + 0x17EDF0) = 1;
    *(int32_t*)((uint8_t*)hEngine + 0x17EDC8) = 1;
    InstallEngineHooks(hEngine);

    // 1. Parse minimal command line (leave default +serverdll = GameServer.dll inside Game\)
    // Enable DebugLevel 6 so Engine_Server.dll logs sm_WriteModelFiles and world events to ConsoleOutputFn
    const char* engineArgs[] = {
        "TheRawServer.exe",
        "-arch", "game",
        "-archcfg", "Default.archcfg",
        "+DebugLevel", "6"
    };
    bool okCmd = pServer->ParseCommandLine(7, engineArgs);
    LogLine("[+] ParseCommandLine -> %s\n", okCmd ? "OK" : "FAIL");

    // 2. Add resource paths (match Default.archcfg 1:1 with TheRaw.exe!)
    const char* resources[] = {
        "Game",
        "Game\\Game.Res00",
        "Game\\Update_1.Res00",
        "Game\\Update_2.Res00",
        "Game\\HD1.Res00",
        "Game\\HD2.Res00",
        "Game\\HD3.Res00",
        "Game\\HD4.Res00",
        "Game\\HD5.Res00",
        "Game\\HD6.Res00",
        "Game\\CustomMod_PTBR.Res00"
    };
    bool okRes = pServer->AddResources(resources, 11);
    LogLine("[+] AddResources (11 archives) -> %s\n", okRes ? "OK" : "FAIL");

    // 3. Init Networking (UDP) & HostGame BEFORE LoadBinaries!
    // (CGameServerShell::OnServerInitialized checks GetTcpIpAddress and internet driver m_Socket)
    bool okNet = pServer->InitNetworking(nullptr, 0);
    printf("[+] InitNetworking -> %s\n", okNet ? "OK" : "FAIL");
    fflush(stdout);

    NetService* pServices = nullptr;
    bool okSvc = pServer->GetServiceList(pServices);
    printf("[+] GetServiceList -> %s (head=%p)\n", okSvc ? "OK" : "FAIL", (void*)pServices);
    HNETSERVICE hSelected = nullptr;
    for (NetService* cur = pServices; cur != nullptr; cur = cur->m_pNext) {
        printf("    Service: handle=%p flags=0x%X name='%s'\n", cur->m_handle, cur->m_dwFlags, cur->m_sName);
        if (!hSelected) hSelected = cur->m_handle;
    }
    fflush(stdout);

    if (hSelected) {
        bool okSel = pServer->SelectService(hSelected);
        printf("[+] SelectService(%p) -> %s\n", hSelected, okSel ? "OK" : "FAIL");
        pServer->FreeServiceList(pServices);
    }

    // 4. HostGame on UDP port
    NetHost hostInfo;
    memset(&hostInfo, 0, sizeof(hostInfo));
    hostInfo.m_Port = port;
    wcsncpy(hostInfo.m_sBindAddr, L"0.0.0.0", 0x21);
    hostInfo.m_dwMaxConnections = 16;
    wcsncpy(hostInfo.m_sName, L"District 187 Local Dedicated", 0xFFF);
    bool okHost = pServer->HostGame(&hostInfo);
    printf("[+] HostGame(port=%u) -> %s (WSAGetLastError=%d)\n",
           (unsigned)port, okHost ? "OK" : "FAIL", WSAGetLastError());

    char ipBuf[64] = {0};
    uint16_t boundPort = 0;
    if (pServer->GetTcpIpAddress(ipBuf, sizeof(ipBuf), boundPort)) {
        printf("[+] Bound UDP endpoint: %s:%u\n", ipBuf, (unsigned)boundPort);
    }
    fflush(stdout);

    // 5. SetGameInfo with VC10-safe ServerGameOptions* (required by CGameServerShell::OnServerInitialized)
    static ServerGameOptions g_GameOpts;
    memset(&g_GameOpts, 0, sizeof(g_GameOpts));
    for (int i = 0; i < 6; ++i) g_GameOpts.s[i].res = 15;
    ServerGameOptions* pOpts = &g_GameOpts;
    bool okInfo = pServer->SetGameInfo(&pOpts, sizeof(pOpts));
    printf("[+] SetGameInfo(&pOpts) -> %s\n", okInfo ? "OK" : "FAIL");
    fflush(stdout);

    // 6. Load GameServer.dll
    bool okBin = pServer->LoadBinaries();
    HMODULE hGS = GetModuleHandleA("GameServer.dll");
    LogLine("[+] LoadBinaries (GameServer.dll) -> %s (hMod=%p, status=0x%X)\n",
           okBin ? "OK" : "FAIL", (void*)hGS, g_GameOpts.status);
    InstallGameServerLogHook(hGS);

    if (!okBin) {
        LogLine("[-] Skipping StartWorld because GameServer.dll did not load.\n");
        pDeleteServer();
        FreeLibrary(hEngine);
        return 4;
    }

    // 6a. Configure GameServer.dll standalone mode + m_sCurLevel (without .World00p extension,
    //     matching GameClient.dll @ 0x10406070 _splitpath comparison -> fixes "Missing LoadingImage String")
    if (hGS) {
        typedef void* (__cdecl* GetNetMgrFn)();
        GetNetMgrFn pGetNetMgr = (GetNetMgrFn)((uint8_t*)hGS + 0x334D0);
        uint8_t* pNetMgr = (uint8_t*)pGetNetMgr();
        if (pNetMgr) {
            pNetMgr[0x6C] = 1; // GameServerNetMgr::m_bStandalone = 1 (allows CPlayerObj::Respawn without RoomServer)
            LogLine("[+] GameServerNetMgr::m_bStandalone = 1 (pNetMgr=%p)\n", (void*)pNetMgr);
        }

        char curLevelNoExt[128] = {0};
        strncpy(curLevelNoExt, worldName, sizeof(curLevelNoExt) - 1);
        char* dot = strrchr(curLevelNoExt, '.');
        if (dot && _stricmp(dot, ".World00p") == 0) *dot = '\0';

        void* pGSShell = *(void**)((uint8_t*)hGS + 0x1E57AC);
        if (pGSShell) {
            typedef void (__thiscall* SetCurLevelFn)(void*, const char*);
            SetCurLevelFn pSetCurLevel = (SetCurLevelFn)((uint8_t*)hGS + 0x55D80);
            pSetCurLevel(pGSShell, curLevelNoExt);
            LogLine("[+] CGameServerShell::SetCurLevel('%s') -> OK\n", curLevelNoExt);

            // Hook CGameServerShell::OnClientEnterWorld (vtable slot 5) to trigger native CPlayerObj::Respawn()
            void** vtbl = *(void***)pGSShell;
            if (vtbl) {
                DWORD oldProt = 0;
                if (VirtualProtect(&vtbl[5], sizeof(void*), PAGE_EXECUTE_READWRITE, &oldProt)) {
                    g_OrigOnClientEnterWorld = (OnClientEnterWorldFn)vtbl[5];
                    vtbl[5] = (void*)&HookedOnClientEnterWorld;
                    VirtualProtect(&vtbl[5], sizeof(void*), oldProt, &oldProt);
                    LogLine("[+] Installed OnClientEnterWorld hook (slot 5, orig=%p)\n", (void*)g_OrigOnClientEnterWorld);
                }
            }
        }
    }

    // 6b. StartWorld
    StartGameRequest req;
    memset(&req, 0, sizeof(req));
    req.m_Type = 3; // STARTGAME_HOST
    strncpy(req.m_WorldName, worldName, sizeof(req.m_WorldName) - 1);
    // Engine_Server.dll CLTServerInterface::StartWorld @ 0x10062259 calls
    // CServerMgr::SetGameInfo(req->m_pGameInfo, req->m_GameInfoLen) (0x100689CF),
    // which frees and clears the previous m_pGameInfo if these fields are NULL/0.
    req.m_pGameInfo = &pOpts;
    req.m_GameInfoLen = sizeof(pOpts);
    bool okWorld = pServer->StartWorld(&req);
    LogLine("[+] StartWorld('%s') -> OK? %s\n", worldName, okWorld ? "OK" : "FAIL");

    // 6c. Advance CServerMissionMgr state to 3 (PLAYING / Active Match — 1=Waiting, 2=PreRound, 3=Playing)
    if (okWorld && hGS) {
        void* pMissionMgr = *(void**)((uint8_t*)hGS + 0x1F1D80);
        if (pMissionMgr) {
            typedef void (__thiscall* SetMissionStateFn)(void*, uint32_t, uint8_t);
            SetMissionStateFn pSetMissionState = (SetMissionStateFn)((uint8_t*)hGS + 0xDEAA0);
            pSetMissionState(pMissionMgr, 3, 1);
            LogLine("[+] CServerMissionMgr::SetMissionState(3 [PLAYING], true) -> OK (pMissionMgr=%p)\n", pMissionMgr);
        }
    }

    // 7. Main server update loop
    LogLine("[*] Entering server tick loop (timeout=%ds)...\n", maxSeconds);
    DWORD startTick = GetTickCount();
    int ticks = 0;
    int lastClients = -1;
    while (g_Running) {
        pServer->Update(0);
        int curClients = pServer->GetNumClients();
        if (curClients != lastClients) {
            LogLine("[*] Active UDP Clients: %d (tick=%d)\n", curClients, ticks);
            if (curClients == 0) {
                g_LastPlayerObj = nullptr;
                g_RespawnDelayTicks = -1;
            }
            lastClients = curClients;
        }
        if (g_LastPlayerObj && g_RespawnDelayTicks > 0) {
            g_RespawnDelayTicks--;
            if (g_RespawnDelayTicks == 0) {
                if (hGS) {
                    void* pMissionMgr = *(void**)((uint8_t*)hGS + 0x1F1D80);
                    if (pMissionMgr) {
                        typedef void (__thiscall* SetMissionStateFn)(void*, uint32_t, uint8_t);
                        SetMissionStateFn pSetMissionState = (SetMissionStateFn)((uint8_t*)hGS + 0xDEAA0);
                        pSetMissionState(pMissionMgr, 3, 1);
                    }
                }
                uint8_t* pPlr = (uint8_t*)g_LastPlayerObj;
                pPlr[0x934] = 1; // m_bClientLoaded = true
                pPlr[0x935] = 1; // m_bReadyToRespawn = true -> triggers CPlayerObj::Respawn() in Update()!
                LogLine("[+] Triggered SetMissionState(3) + native CPlayerObj::Respawn() on %p (+0x934=1, +0x935=1)\n", g_LastPlayerObj);
            }
        }
        ticks++;
        Sleep(16); // ~60Hz
        if (maxSeconds > 0 && (int)((GetTickCount() - startTick) / 1000) >= maxSeconds) {
            LogLine("[*] Timeout reached (%ds, %d ticks). Shutting down cleanly...\n", maxSeconds, ticks);
            break;
        }
    }

    pDeleteServer();
    FreeLibrary(hEngine);
    LogLine("[+] Server shut down gracefully.\n");
    if (g_LogFile) fclose(g_LogFile);
    return 0;
}
