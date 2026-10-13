import json
import os
import urllib.request
import urllib.parse
import time

# Стартовый костяк запросов
DEFAULT_QUERIES = [
    {"q": "Выключатель нагрузки 2P 25А", "group": "Автоматика", "unit": "шт.", "tags": "рубильник вн 25а 25a выключатель нагрузки"},
    {"q": "Выключатель нагрузки 2P 40А", "group": "Автоматика", "unit": "шт.", "tags": "рубильник вн 40а 40a выключатель нагрузки"},
    {"q": "Выключатель нагрузки 2P 63А", "group": "Автоматика", "unit": "шт.", "tags": "рубильник вн 63а 63a выключатель нагрузки"},
    {"q": "Рубильник реверсивный 40А", "group": "Автоматика", "unit": "шт.", "tags": "рубильник реверсивный перекидной генератор ибп"},
    {"q": "Автоматический выключатель 1P 16A C", "group": "Автоматика", "unit": "шт.", "tags": "автомат ав 16а 16a розетки"},
    {"q": "Автоматический выключатель 1P 10A C", "group": "Автоматика", "unit": "шт.", "tags": "автомат ав 10а 10a свет"},
    {"q": "УЗО 2P 40A 30mA", "group": "Автоматика", "unit": "шт.", "tags": "узо вдт диф 40а 30ма"},
    {"q": "Дифавтомат 16A 30mA", "group": "Автоматика", "unit": "шт.", "tags": "дифавтомат авдт диф 16а"},
    {"q": "Реле напряжения 63А", "group": "Автоматика", "unit": "шт.", "tags": "реле напряжения ркн зубр меандр 63а"},
    {"q": "Контактор модульный 25А", "group": "Автоматика", "unit": "шт.", "tags": "контактор км 25а мастер выключатель"},
    {"q": "Вилка штепсельная 16А с заземлением", "group": "Розетки и вилки", "unit": "шт.", "tags": "вилка прямая угловая для розетки 16а"},
    {"q": "Розетка 1-м с заземлением AtlasDesign", "group": "Розетки и вилки", "unit": "шт.", "tags": "розетка встраиваемая механизм 16а"},
    {"q": "Выключатель 1-клавишный AtlasDesign", "group": "Розетки и вилки", "unit": "шт.", "tags": "выключатель свет клавиша"},
    {"q": "Кабель ВВГнг(А)-LS 3х2.5", "group": "Кабель", "unit": "м.п.", "tags": "кабель ввг 3х2.5 3*2.5"},
    {"q": "Кабель ВВГнг(А)-LS 3х1.5", "group": "Кабель", "unit": "м.п.", "tags": "кабель ввг 3х1.5 3*1.5"},
    {"q": "Провод ПВС 3х2.5", "group": "Кабель", "unit": "м.п.", "tags": "провод пвс мягкий удлинитель вилка"},
    {"q": "Клемма строительная WAGO", "group": "Автоматика", "unit": "шт.", "tags": "клемма ваго wago коробка"},
]

USER_QUERIES_FILE = "user_queries.json"

def detect_unit_and_group(query_text):
    q = query_text.lower()
    if any(w in q for w in ["кабель", "провод", "ввг", "пвс", "пугв", "гофра", "труба", "лоток", "кабель-канал"]):
        return "Кабель", "м.п."
    if any(w in q for w in ["розетк", "вилк", "выключател", "рамк", "диммер"]):
        return "Розетки и вилки", "шт."
    if any(w in q for w in ["щит", "бокс", "корпус", "шкаф"]):
        return "Щиты и боксы", "шт."
    return "Автоматика", "шт."

def load_all_queries():
    # Загружаем накопленные запросы пользователей из файла
    saved_user_queries = []
    if os.path.exists(USER_QUERIES_FILE):
        try:
            with open(USER_QUERIES_FILE, "r", encoding="utf-8") as f:
                saved_user_queries = json.load(f)
        except Exception:
            saved_user_queries = []

    # Проверяем, прилетели ли новые поисковые запросы через GitHub Issues или параметр запуска
    new_query_env = os.environ.get("NEW_USER_QUERY", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")

    newly_added = []
    if new_query_env:
        newly_added.append(new_query_env)

    # Собираем открытые заявки с тегом [SEARCH] из GitHub Issues
    if repo and token:
        try:
            issues_url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=30"
            req = urllib.request.Request(issues_url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "SmetaMAX-Bot"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                issues = json.loads(resp.read().decode("utf-8"))
                for iss in issues:
                    title = iss.get("title", "")
                    if title.startswith("[SEARCH]"):
                        clean_q = title.replace("[SEARCH]", "").strip()
                        if len(clean_q) >= 2:
                            newly_added.append(clean_q)
                        # Закрываем обработанный запрос, чтобы не висел
                        close_url = f"https://api.github.com/repos/{repo}/issues/{iss['number']}"
                        close_data = json.dumps({"state": "closed"}).encode("utf-8")
                        close_req = urllib.request.Request(close_url, data=close_data, method="PATCH", headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json",
                            "Content-Type": "application/json",
                            "User-Agent": "SmetaMAX-Bot"
                        })
                        urllib.request.urlopen(close_req, timeout=10)
        except Exception as e:
            print(f"Инфо по очереди Issues: {e}")

    existing_q_strings = {x["q"].lower() for x in DEFAULT_QUERIES + saved_user_queries}

    for nq in newly_added:
        for line in nq.split(","):
            clean = line.strip()
            if len(clean) >= 2 and clean.lower() not in existing_q_strings:
                grp, unit = detect_unit_and_group(clean)
                saved_user_queries.append({
                    "q": clean,
                    "group": grp,
                    "unit": unit,
                    "tags": clean.lower()
                })
                existing_q_strings.add(clean.lower())
                print(f"➕ Добавлен новый запрос от пользователя в вечную базу: {clean}")

    # Сохраняем пополненный список запросов пользователей обратно в репозиторий
    with open(USER_QUERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(saved_user_queries, f, ensure_ascii=False, indent=2)

    return saved_user_queries + DEFAULT_QUERIES

def fetch_etm_items(query_obj):
    q = query_obj["q"]
    url = f"https://ipro.etm.ru/api/v1/goods?name={urllib.parse.quote(q)}&rows=4"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rows = data.get("data", {}).get("rows", [])
            for idx, r in enumerate(rows):
                raw_price = r.get("price") or r.get("price_retail") or r.get("price_m")
                try:
                    price = float(str(raw_price).replace(",", ".").strip())
                except Exception:
                    price = 0.0

                if price <= 0:
                    continue

                name = r.get("name") or q
                brand = r.get("brand") or r.get("mnf_name") or ""
                full_name = f"{name} ({brand})" if brand and brand.lower() not in name.lower() else name

                results.append({
                    "id": f"parsed_{abs(hash(full_name)) % 1000000}_{idx}",
                    "group": query_obj["group"],
                    "tags": f"{query_obj['tags']} {full_name.lower()}",
                    "name": full_name,
                    "category": "material",
                    "unit": query_obj["unit"],
                    "stores": {
                        "ЭТМ (живая цена)": round(price),
                        "ВсеИнструменты (~)": round(price * 1.04),
                        "Лемана ПРО (~)": round(price * 0.97),
                        "Электромонтаж (~)": round(price * 1.12)
                    }
                })
    except Exception as e:
        print(f"Ошибка при запросе '{q}': {e}")
    return results

def main():
    all_queries = load_all_queries()
    all_items = []
    seen_names = set()

    for q_obj in all_queries:
        print(f"Парсим: {q_obj['q']}...")
        items = fetch_etm_items(q_obj)
        for item in items:
            if item["name"] not in seen_names:
                seen_names.add(item["name"])
                all_items.append(item)
        time.sleep(0.4)

    with open("prices.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"Готово! Собрано и сохранено позиций: {len(all_items)}")

if __name__ == "__main__":
    main()
