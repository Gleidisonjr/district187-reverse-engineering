# S2 Launcher — kaynak kodu

Bu klasör, oyunu güncelleyip başlatan **S2Launcher.exe**'nin tam kaynak kodudur.
Oyunla birlikte gelir; çünkü çalıştırdığınız programın ne yaptığını görmeye
hakkınız var.

---

## "Bu exe virüs mü?"

Bize güvenmek zorunda değilsiniz. İki yolunuz var:

### 1. Kendiniz derleyin

**`derle.cmd`** dosyasına çift tıklayın. Kullandığı derleyici Windows'un içinde
zaten hazır gelir — hiçbir şey indirilmez, kurulmaz. Birkaç saniyede bir üst
klasöre, yani oyun klasörüne **`S2Launcher.exe`** çıkar ve mevcut olanın yerine
geçer. Artık elinizdeki program, okuduğunuz koddan **sizin ürettiğiniz**
programdır.

Değişikliğinizin güncellemelerden sonra da kalmasını istiyorsanız
`derle.cmd -ozel` kullanın — aşağıda anlatılıyor.

### 2. Verilen exe'yi geri okuyun

`S2Launcher.exe` bir .NET programıdır. [ILSpy](https://github.com/icsharpcode/ILSpy)
gibi ücretsiz bir araçla açtığınızda neredeyse birebir kaynak koda geri çevrilir
ve bu klasördeki dosyalarla karşılaştırabilirsiniz. Kod karartma (obfuscation)
veya paketleme (packing) **yapılmamıştır** — bilerek.

> **Hash karşılaştırmasıyla doğrulama yapılamaz — dikkat.**
> `derle.cmd` size bir SHA-256 gösterir ama bu, paylaşılan `S2Launcher.exe`'nin
> hash'iyle **asla aynı çıkmaz** ve bu bir kurcalama belirtisi *değildir*.
> Sebebi teknik: Windows ile gelen C# derleyicisi her derlemeye ayrı bir kimlik
> gömüyor, dolayısıyla aynı kaynak koddan her seferinde farklı baytlar çıkıyor
> (`/deterministic` seçeneği bu derleyicide yok).
> Gösterilen hash **kendi kopyanız** içindir: sonradan biri onu değiştirdi mi
> diye bakmak için işe yarar.
> Gerçek doğrulama yolu ikisidir: **kaynağı okuyup kendiniz derlemek**, ya da
> **verilen exe'yi ILSpy ile açıp kodu bu klasördekiyle karşılaştırmak.**

> Windows imzasız programlarda "Windows bilgisayarınızı korudu" uyarısı verir.
> *Ek bilgi → Yine de çalıştır*. Kod imzalama sertifikası yıllık ücretli olduğu
> için imzalanmıyor. İçiniz rahat etmiyorsa 1. yolu kullanın.

---

## Launcher ne yapar, ne yapmaz

**Yapar:**

- Sunucudan dosya listesi (`manifest.json`) indirir
- Oyun klasörünüzdeki dosyaların SHA-256 parmak izini hesaplar
- Yalnızca **değişmiş/eksik** olanları indirir — her seferinde 1 GB değil
- İndirdiği her dosyayı **doğrular**; parmak izi tutmazsa dosyayı çöpe atar ve
  oyununuza dokunmaz
- `launcher.cfg`'de yazan oyunu başlatır
- Oyun açıkken ApexGuard anti-hile raporunu (kalp atışı, ihlal kaydı) sunucuya taşır ve `%LOCALAPPDATA%\S2Rebirth\apex-kopru.log` dosyasına kısa bir günlük yazar — "anti-hile çalışmıyor" diye maça alınmadıysanız istenecek dosya budur

**Yapmaz:**

- Kayıt defterine (registry) dokunmaz
- Oyun klasörünün **dışına** tek bayt yazmaz
- Yönetici yetkisi istemez
- Bilgisayarınızdan bilgi toplamaz, hiçbir yere veri göndermez
- Arka planda kalmaz — oyun açılınca kapanır

Tek ağ trafiği, `launcher.cfg` içinde **açıkça yazan** adrese yapılan indirme
istekleridir. O dosyayı Not Defteri ile açıp görebilirsiniz; gizli bir adres yok.

---

## Tek launcher

Oyunla birlikte **tek** launcher geliyor: `S2Launcher.exe`. Ayrı bir "özel"
sürüm dağıtmıyoruz — ayarlarınız zaten `launcher-ozel.cfg` içinde korunuyor
(aşağıya bakın), o yüzden ikinci bir exe'ye gerek kalmadı.

Yine de kendi derlemenizi kalıcı tutmak isterseniz `derle.cmd -ozel`
seçeneği duruyor: ürettiği `S2Launcher-ozel.exe` dosyasına güncelleme
hiçbir zaman dokunmaz.

---

## Ayarlar penceresi

Sağ üstteki **dişli** düğmesi. Sunucu adresi, port, çözünürlük, pencereli
mod, Discord bağlantısı — hepsi buradan.

**Nereye yazar:** `launcher-ozel.cfg`. Resmî `launcher.cfg`'ye **değil.**

Bu bilerek böyle:

- Adında `-ozel` geçtiği için o dosya **yayına hiç girmez**; güncelleme de
  bütünlük denetimi de ona dokunamaz. Ayarınız hiçbir koşulda sıfırlanmaz.
- Resmî `launcher.cfg` güncellenmeye devam eder. Sunucu adresi değişirse
  yeni adresi alırsınız — ayarlarınıza gömülü kalmazsınız.
- **Yalnızca değiştirdiğiniz satır yazılır.** `kaynak` alanına dokunmadıysanız
  o satır özel dosyaya hiç girmez.
- Varsayılana dönmek: `launcher-ozel.cfg` dosyasını silin.

Alt satırdaki `[x] Pencereli çalıştır` tiki de aynı yere yazılıyor; artık
launcher kapanınca kaybolmuyor.

### Oyunu yeniden kur

Ayarlar penceresinin altındaki kırmızı yazı. **Her şeyi sıfırlar:**
sunucudaki listedeki her dosya baştan indirilir ve normalde korunan
dosyaların (`settings.cfg`, `Profile000.gdb`, `launcher.cfg`,
`Default.archcfg`) da üzerine yazılır. ~1 GB iner.

İki kez onay sorar. Sizin `launcher-ozel.cfg` dosyanıza dokunmaz.

---

## HD grafik paketi

Alt satırdaki **`[ ] HD grafik paketi`** yazısına tıklayınca açılır/kapanır.
Her iki yönde de önce onay sorar, kabul etmeden hiçbir şey yapmaz.

**Açtığınızda**

- Yaklaşık **1,7 GB** iner (ayrı bir adresten — `launcher.cfg` → `hd_kaynak`)
- Oyun klasörüne **iki dosya** kurulur: `Game\HD.Res00` ve `Game\HD.ResDt`
- `Default.archcfg`'ye bir satır eklenir; oyun o arşivi de yükler
- Silah, kıyafet ve harita dokuları iki kat çözünürlüğe çıkar

**Kapattığınızda**

- Yalnızca o iki dosya silinir, satır geri alınır
- Diskten ~1,8 GB boşalır
- **Oyunun kendi dosyalarına dokunulmaz** — HD paketi hiçbir şeyin üzerine
  yazmaz, yanına eklenir

İnternet kesilir ya da HD adresi cevap vermezse oyun **standart dokularla**
açılır; yarım inmiş bir paket yüzünden oyun açılamaz duruma gelmez.

`launcher.cfg` içinde `hd_kaynak` satırı boşsa bu seçenek hiç görünmez.

---

## Özelleştirmek isterseniz

Launcher'ı istediğiniz gibi değiştirebilirsiniz. Tek kural şu:

> ### Adında `-ozel` geçen hiçbir şeye güncelleme dokunmaz.

Güncelleyici yalnızca sunucudaki listede olan dosyaları yönetir. `-ozel` ekli
dosyalar o listede olmadığı için ne değiştirilir ne silinir.

### Doğru yol

**Bu klasörün içinde rahatça çalışabilirsiniz.** `acik-kaynak-launcher\`
klasörü bir kez kurulur ve **bir daha asla üstüne yazılmaz** — güncelleme
buradaki dosyalara dokunmaz.

`kaynak\` içindeki `.cs` dosyalarında istediğinizi değiştirin, sonra
`derle.cmd` çalıştırın. **İki kip var, farkı önemli:**

| Komut | Ürettiği dosya | Güncellemede |
|---|---|---|
| `derle.cmd` (çift tıklama) | `..\S2Launcher.exe` | **geri alınır** — resmî sürüm iner |
| `derle.cmd -ozel` | `..\S2Launcher-ozel.exe` | **kalıcı** — dokunulmaz |

Yani sadece denemek/bakmak istiyorsanız çift tıklayın, oyunun launcher'ı
değişir. Değişikliğinizin **kalıcı** olmasını istiyorsanız `-ozel` ile
derleyin ve oyunu bundan sonra `S2Launcher-ozel.exe` ile açın.

`-ozel` ile derlemek için: klasörde boş bir yere `Shift + sağ tık` →
*Burada PowerShell penceresi aç* → `.\derle.cmd -ozel`

> **Bunun bir bedeli var, bilin:** klasör hiç güncellenmediği için, biz
> launcher'da bir hata düzeltirsek sizin buradaki kodunuz **eski kalır**.
> Resmî `S2Launcher.exe` güncellenmeye devam eder, yani ikisi zamanla ayrışır.
> Launcher'daki **Bütünlük Denetimi** bunu size açıkça söyler: farklı olan
> dosyaları listeler. Güncel kaynağı istiyorsanız bu klasörü silip launcher'ı
> yeniden açın — en yeni hâli iner. (Önce kendi değişikliklerinizi yedekleyin.)

Ayar değiştirmek yeterliyse kod yazmanıza gerek yok: oyun klasörüne
**`launcher-ozel.cfg`** adında bir dosya açın, yalnızca değiştirmek istediğiniz
satırları yazın. O dosya resmî `launcher.cfg`'nin **üstüne** uygulanır.

```ini
# launcher-ozel.cfg — yalnizca degistirmek istediklerinizi yazin
pencereli = 0
genislik  = 2560
yukseklik = 1440
```

### Neye dokunulur, neye dokunulmaz

| Dosya | Güncellemede |
|---|---|
| `S2Launcher.exe`, `launcher.cfg`, `varliklar\`, oyun dosyaları | **yenilenir** |
| `acik-kaynak-launcher\` | **bir kez kurulur, dokunulmaz** |
| `S2Launcher-ozel.exe`, `launcher-ozel.cfg` | **dokunulmaz** |
| `settings.cfg` (çözünürlük, grafik) | **dokunulmaz** |
| `Profiles\Profile000.gdb` (profil, tuşlar) | **dokunulmaz** |

Son iki satır neden böyle: oyun bu dosyaları her çıkışta kendisi yazıyor. Normal
dosya gibi ele alsaydık her güncelleme ayarlarınızı sıfırlardı.

---

## Bütünlük denetimi

Launcher normalde **her açılışta** her dosyanın SHA-256 parmak izini sunucudaki
listeyle karşılaştırır ve yalnızca tutmayanları indirir. Eksik dosya, bozulmuş
dosya, yeni sürüm — hepsi böyle bulunur. Yani 1 GB yalnızca ilk kurulumda iner.

Hız için küçük bir kısayol var: dosyanın **boyutu ve tarihi** değişmediyse
yeniden hesaplanmaz (1 GB'ı her açılışta hesaplamak ~15 saniye sürerdi).

Bu kısayol tek bir durumu kaçırır: biri dosyayı **aynı boyutta** değiştirip
**tarihini geri alırsa**. İşte o zaman **BÜTÜNLÜK DENETİMİ** düğmesini kullanın:

- Kısayolu tamamen yok sayar, her dosyayı baştan hesaplar
- Bozuk/eksik olanı yeniden indirir
- Sizin dosyalarınız (`settings.cfg`, profil, bu kaynak klasörü) resmî sürümden
  farklıysa **bildirir ama dokunmaz** — hangileri olduğunu listeler

Komut satırından da çalışır:

```
S2Launcher.exe --butunluk
```

Oyun tuhaf davranıyorsa, bir dosyayı yanlışlıkla sildiyseniz veya "acaba biri
oynadı mı" diye merak ediyorsanız bunu çalıştırın.

---

## Dosyalar

```
acik-kaynak-launcher\
  derle.cmd            derler  ->  ..\S2Launcher.exe  (-ozel ile ..\S2Launcher-ozel.exe)
  OKUBENI.md           bu dosya
  kaynak\
    Program.cs         giriş noktası + launcher.cfg okuyucu
    Guncelleyici.cs    parmak izi karşılaştırma ve indirme motoru
    AnaPencere.cs      arayüz
    app.manifest       DPI ayarı + "yönetici yetkisi isteme" bildirimi
    s2.ico             exe'nin simgesi (16-256 px, 7 boyut)
```

Simgeyi değiştirmek isterseniz `s2.ico` yerine kendi `.ico` dosyanızı koyun —
`derle.cmd` onu gömer. PNG olmaz, gerçek ICO gerekir.

### Proje beyanı metni

**PROJE BEYANI** düğmesi tarayıcı açmaz; metin launcher'ın içinde,
kaydırılabilir bir pencerede gösterilir. Metin `AnaPencere.cs` içindeki `BEYAN`
dizisindedir:

```csharp
static readonly string[] BEYAN = {
    "# Başlık satırı",          // "#" ile başlayan satır BAŞLIK olur
    "Normal paragraf.",
    "",                          // boş satır = paragraf aralığı
};
```

Değiştirip `derle.cmd` çalıştırmanız yeterli. Beyanın uygulamayla aynı sürümde
olması için bilerek koda gömülü — internet olmasa da, site kapansa da okunur.

---

## Görselleri değiştirmek (kod yazmadan)

Arka planı ya da armayı değiştirmek için koda dokunmanıza gerek yok. Oyun
klasöründe **`varliklar-ozel\`** adında bir klasör açın ve aynı adlarla kendi
dosyalarınızı koyun:

```
<oyun klasörü>\
   varliklar\            resmî görseller  (güncellemede yenilenir)
   varliklar-ozel\       SİZİN görselleriniz  (dokunulmaz)
      launcher-background.jpg
      s2-logo.png
```

Launcher önce `varliklar-ozel\` içine bakar, bulamazsa resmîye düşer. Yalnızca
değiştirmek istediğiniz dosyayı koymanız yeterli — ikisini birden koymak
zorunda değilsiniz.

`-ozel` ekli olduğu için bu klasör güncellemede **asla** silinmez veya
değiştirilmez.

> Arka plan tam ekrana yayılır (oranı korunur, taşan kısım kırpılır), arma
> ortada 96 piksel yüksekliğinde çizilir. En iyi sonuç için arka planı geniş,
> armayı da saydam PNG verin.
