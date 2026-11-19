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

// ServerAppHandler callback interface (LithTech Jupiter EX)
class ServerAppHandler {
public:
    virtual ~ServerAppHandler() {}
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

    // 1. Parse minimal command line (leave default +serverdll = GameServer.dll inside Game\)
    const char* engineArgs[] = {
        "D187_ServerHost.exe",
        "-arch", "game"
    };
    bool okCmd = pServer->ParseCommandLine(3, engineArgs);
    printf("[+] ParseCommandLine -> %s\n", okCmd ? "OK" : "FAIL");
    fflush(stdout);

    // 2. Add resource paths
    const char* resources[] = {
        "Game",
        "Game\\Game.Res00",
        "Game\\Update_1.Res00",
        "Game\\Update_2.Res00"
    };
    bool okRes = pServer->AddResources(resources, 4);
    printf("[+] AddResources -> %s\n", okRes ? "OK" : "FAIL");
    fflush(stdout);

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
    printf("[+] LoadBinaries (GameServer.dll) -> %s (hMod=%p, status=0x%X)\n",
           okBin ? "OK" : "FAIL", (void*)GetModuleHandleA("GameServer.dll"), g_GameOpts.status);
    fflush(stdout);

    if (!okBin) {
        printf("[-] Skipping StartWorld because GameServer.dll did not load.\n");
        pDeleteServer();
        FreeLibrary(hEngine);
        return 4;
    }

    // 6. StartWorld
    StartGameRequest req;
    memset(&req, 0, sizeof(req));
    req.m_Type = 3; // STARTGAME_HOST
    strncpy(req.m_WorldName, worldName, sizeof(req.m_WorldName) - 1);
    bool okWorld = pServer->StartWorld(&req);
    printf("[+] StartWorld('%s') -> %s\n", worldName, okWorld ? "OK" : "FAIL");
    fflush(stdout);

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
            lastClients = curClients;
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
