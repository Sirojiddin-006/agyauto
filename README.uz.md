# agyauto

[English](README.md) · [Özbekça](README.uz.md)

Ruxsat sörovlarini qölda tasdiqlaşdan çarçadingizmi? `agyauto` buyruqni (`agy`, yoki agy işlatadigan serverga `ssh`) özining
pseudo-terminalida yuritadi va agy'ning "Run this command? / Accept this file edit? / Allow creation of this file?" sörovlariga
özi javob beradi. Hamma sessiyalarni kuzatiş, töxtatiş va tarixini köriş uçun [btop](https://github.com/aristocratos/btop)
uslubidagi dashboard bor.

```
curl -fsSL https://raw.githubusercontent.com/Sirojiddin-006/agyauto/main/install.sh | sh
```

Linux va macOS, Python 3.8+ (faqat standart kutubxona). Windows: hozirça WSL orqali.

## Işlatiş

```sh
agyauto agy                    # lokal agy
agyauto ssh user@server        # keyin serverda agy'ni işga tuşiring
agyauto --name build ssh ci    # sessiyaga nom beriş
agyauto                        # dashboard (istalgan boşqa terminal / workspace'dan)
```

Tugma töğridan-töğri öralgan buyruqning pty'siga yoziladi. Oyna fokusi, klaviaturangiz yoki boşqa workspace'larga
tegmaydi, şuning uçun boşqa işlaringizni bemalol qilaverasiz. Istagança sessiya işga tuşiriş mumkin, har biri mustaqil.

### Dashboard

| Tugma | |
|---|---|
| `1`-`5` / Tab | Sessiyalar · Jonli · Tarix · Statistika · Sozlamalar |
| `j` `k` | sessiya / qatorni tanlaş |
| `p` | tanlangan sessiyani töxtatiş / davom ettiriş |
| `d` | tanlangan sessiyada **dangermode** yoqiş/öçiriş |
| `r` | sessiyaga nom beriş |
| `f` `/` `Enter` | Tarix: tur filtri, qidiruv, batafsil |
| `L` | English ⇄ Özbekça |
| `q` | çiqiş |

Dashboard'dagi özgarişlar işlab turgan sessiyalarga taxminan bir soniyada yetadi. Qayta işga tuşiriş kerak emas, ssh uzilmaydi.

### Xavfsizlik

* Faqat **1-variant** yuboriladi (Enter, yoki `--key 1` bilan `1`). "Always allow (persist to settings.json)" variantlari heç qaçon tanlanmaydi.
* **`/` yoki `~` ni öçiriş (`rm -rf /`, `--no-preserve-root`, ...) heç qaçon tasdiqlanmaydi**, dangermode'da ham. Sörov ekranda
  qoladi, terminal qönğiroq beradi, desktop bildirişnoma yuboriladi va hodisa `BLOCKED` deb yoziladi.
* Öz taqiq qoidalaringizni (regex) Sozlamalarda yoki `agyauto config set deny 'rm -rf|DROP TABLE'` bilan qöşing.
* **Dangermode** qolgan HAMMA narsani, jumladan `press ctrl+j to approve` yoki `(y/n)` kabi nomaʼlum sörovlarni ham tasdiqlaydi.
  Standart holatda öçiq, har bir sessiyada tasdiqlaş söralgandan keyin yoqiladi.
* Siz şu terminalda yozayotgan paytda heç narsa yuborilmaydi.
* Token, parol va kalitlar tarixga yozilişidan yoki jonli körinişda çiqişidan oldin yaşiriladi. Holat papkasi yopiq (`0700`/`0600`).

Tanilmagan sörovlar `STALLED` deb (yaşirilgan ekran nusxasi bilan) yoziladi, şunda pattern qöşiş mumkin. Öşa nusxani issue'da yuboring.

## Buyruqlar

```
agyauto status [--json]          ishlayotgan sessiyalar
agyauto history [-n N] [--kind APPROVED|BLOCKED|STALLED] [-s MATN]
agyauto config [get|set KALIT QIYMAT]   lang, key, delay, notify, retention_days, danger_default, deny
agyauto lang en|uz
agyauto doctor
agyauto update
agyauto uninstall [--purge]
```

Fayllar: `~/.config/agyauto/config.json`, `~/.local/state/agyauto/` (history.db, jonli sessiya fayllari), dastur `~/.local/share/agyauto/` da.
Tarix standart böyiça 90 kun saqlanadi.

## Işlab çiqiş

```sh
python3 -m unittest discover -s tests -v
```

MIT litsenziya.
