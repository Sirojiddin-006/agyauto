# agyauto

[English](README.md) · [O'zbekcha](README.uz.md)

Ruxsat so'rovlarini qo'lda tasdiqlashdan charchadingizmi? `agyauto` buyruqni (`agy`, yoki agy ishlatadigan serverga `ssh`) o'zining
pseudo-terminalida yuritadi va agy'ning "Run this command? / Accept this file edit? / Allow creation of this file?" so'rovlariga
o'zi javob beradi. Hamma sessiyalarni kuzatish, to'xtatish va tarixini ko'rish uchun [btop](https://github.com/aristocratos/btop)
uslubidagi dashboard bor.

```
curl -fsSL https://raw.githubusercontent.com/Sirojiddin-006/agyauto/main/install.sh | sh
```

Linux va macOS, Python 3.8+ (faqat standart kutubxona). Windows: hozircha WSL orqali.

## Ishlatish

```sh
agyauto agy                    # lokal agy
agyauto ssh user@server        # keyin serverda agy'ni ishga tushiring
agyauto --name build ssh ci    # sessiyaga nom berish
agyauto                        # dashboard (istalgan boshqa terminal / workspace'dan)
```

Tugma to'g'ridan-to'g'ri o'ralgan buyruqning pty'siga yoziladi. Oyna fokusi, klaviaturangiz yoki boshqa workspace'larga
tegmaydi, shuning uchun boshqa ishlaringizni bemalol qilaverasiz. Istagancha sessiya ishga tushirish mumkin, har biri mustaqil.

### Dashboard

| Tugma | |
|---|---|
| `1`-`5` / Tab | Sessiyalar · Jonli · Tarix · Statistika · Sozlamalar |
| `j` `k` | sessiya / qatorni tanlash |
| `p` | tanlangan sessiyani to'xtatish / davom ettirish |
| `d` | tanlangan sessiyada **dangermode** yoqish/o'chirish |
| `r` | sessiyaga nom berish |
| `f` `/` `Enter` | Tarix: tur filtri, qidiruv, batafsil |
| `L` | English ⇄ O'zbekcha |
| `q` | chiqish |

Dashboard'dagi o'zgarishlar ishlab turgan sessiyalarga taxminan bir soniyada yetadi. Qayta ishga tushirish kerak emas, ssh uzilmaydi.

### Xavfsizlik

* Faqat **1-variant** yuboriladi (Enter, yoki `--key 1` bilan `1`). "Always allow (persist to settings.json)" variantlari hech qachon tanlanmaydi.
* **`/` yoki `~` ni o'chirish (`rm -rf /`, `--no-preserve-root`, ...) hech qachon tasdiqlanmaydi**, dangermode'da ham. So'rov ekranda
  qoladi, terminal qo'ng'iroq beradi, desktop bildirishnoma yuboriladi va hodisa `BLOCKED` deb yoziladi.
* O'z taqiq qoidalaringizni (regex) Sozlamalarda yoki `agyauto config set deny 'rm -rf|DROP TABLE'` bilan qo'shing.
* **Dangermode** qolgan HAMMA narsani, jumladan `press ctrl+j to approve` yoki `(y/n)` kabi noma'lum so'rovlarni ham tasdiqlaydi.
  Standart holatda o'chiq, har bir sessiyada tasdiqlash so'ralgandan keyin yoqiladi.
* Siz shu terminalda yozayotgan paytda hech narsa yuborilmaydi.
* Token, parol va kalitlar tarixga yozilishidan yoki jonli ko'rinishda chiqishidan oldin yashiriladi. Holat papkasi yopiq (`0700`/`0600`).

Tanilmagan so'rovlar `STALLED` deb (yashirilgan ekran nusxasi bilan) yoziladi, shunda pattern qo'shish mumkin. O'sha nusxani issue'da yuboring.

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
Tarix standart bo'yicha 90 kun saqlanadi.

## Ishlab chiqish

```sh
python3 -m unittest discover -s tests -v
```

MIT litsenziya.
