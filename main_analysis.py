"""
Программа "QRP‑Stat" предназначен для  анализа файла ADIF для вывода статистики по странам и локаторам в зависимости от используемой мощности. Результаты анализа ориентированы на таблицы активности Клуба 72: http://club-72.ru/#qrp.

Данный скрипт создан на основе кода, написанного Андреем UB3BBB. Далее код доработан совместными усилиями двух искусственных интеллектов — Manus и DeepSeek. Они помогли структурировать логику и сделать анализ максимально полезным.

Скрипт распространяется по принципу «как есть» (AS IS): авторы и ИИ-помощники не несут ответственности за возможные ошибки, потерю данных или неверные расчёты. Никаких претензий, исков или требований не принимается. Однако мы будем очень рады, если вы поделитесь найденными проблемами, конструктивной критикой или идеями по улучшению. 

Пишите на почту: andrey.R4NCU@gmail.com. Ваше мнение поможет сделать скрипт лучше для всех.
"""
import sys
import os
import re
from datetime import datetime
from collections import Counter, defaultdict
import adif_io
from pyhamtools import locator, LookupLib, Callinfo
import time

def parse_power_custom(pwr_str):
    """Парсинг мощности из строки"""
    if not pwr_str:
        return 99999.0
    pwr_str = str(pwr_str).replace(',', '.')
    if pwr_str == "" or (not re.search(r'^[\d\.\s]+', pwr_str)):
        return 99999.0
    dig_sel = re.search(r'[(\d+\.?\d*)|(\.\d+)]+', pwr_str)
    if dig_sel:
        try:
            return float(dig_sel.group())
        except:
            return 99999.0
    return 99999.0

def get_base_call(call):
    """Извлекает базовый позывной, удаляя суффиксы и префиксы через слэш"""
    if not call:
        return ""
    parts = call.upper().split('/')
    if len(parts) == 1:
        return parts[0]
    return max(parts, key=len)

def normalize_locator(loc):
    """Дополняет 4-значный локатор до 6-значного (MM)"""
    if not loc:
        return ""
    loc = loc.strip().upper()
    loc = re.sub(r'[^A-Z0-9]', '', loc)
    if len(loc) == 4:
        return loc + "MM"
    if len(loc) >= 6:
        return loc[:6]
    return loc

def get_call_info(call, cic, max_retries=3):
    """Получение информации о позывном с повторами"""
    if not call or not cic:
        return None, None
    
    for attempt in range(max_retries):
        try:
            # Получаем локатор
            loc = None
            try:
                pos = cic.get_lat_long(call)
                if pos and 'latitude' in pos and 'longitude' in pos:
                    loc = locator.latlong_to_locator(pos["latitude"], pos["longitude"])
                    loc = normalize_locator(loc)
            except:
                pass
            
            # Получаем страну
            country = None
            try:
                country = cic.get_country_name(call).upper()
            except:
                pass
            
            if loc or country:
                return loc, country
            
            time.sleep(0.5)
        except:
            time.sleep(1)
    
    return None, None

def calculate_distance_approx(loc1, loc2):
    """Приблизительный расчет расстояния между локаторами"""
    try:
        def loc_to_coords(loc):
            loc = loc.upper()
            lon = (ord(loc[0]) - 65) * 20 + (ord(loc[2]) - 48) * 2
            if len(loc) >= 5:
                lon += (ord(loc[4]) - 65) * (2/24)
            lat = (ord(loc[1]) - 65) * 10 + (ord(loc[3]) - 48)
            if len(loc) >= 6:
                lat += (ord(loc[5]) - 65) * (1/24)
            return lat - 90, lon - 180
        
        lat1, lon1 = loc_to_coords(loc1)
        lat2, lon2 = loc_to_coords(loc2)
        
        R = 6371
        lat1, lon1, lat2, lon2 = map(lambda x: x * 3.14159 / 180, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (dlat/2)**2 + (dlon/2)**2 * (lat1 + lat2)/2
        c = 2 * (a**0.5) if a <= 1 else 2
        return R * c
    except:
        return 0

def analyze_files(file_list, my_loc_str, output_file, power_override=None):
    """Анализирует список ADIF файлов и сохраняет общую статистику в один файл"""
    
    print(f"Начинаю анализ {len(file_list)} файлов...")
    if power_override is not None:
        print(f"Задана мощность для всех связей: {power_override} Вт")
    my_loc_str = normalize_locator(my_loc_str)
    
    # Инициализируем библиотеку для поиска информации
    print("Загружаю базу данных позывных...")
    cic = None
    try:
        lib = LookupLib(lookuptype="countryfile")
        cic = Callinfo(lib)
        print("База данных загружена успешно")
    except Exception as e:
        print(f"Не удалось загрузить базу данных: {e}")
        print("Будут использованы только данные из ADIF файла")
    
    # Общая статистика для всех файлов
    # [name, max_pwr, count, [dist, call, pwr], countries, fields, squares]
    act_list = [
        ["ALL", float('inf'), 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRP", 5.0, 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRPp", 1.0, 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRP-X", 0.1, 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRPu", 0.01, 0, [0.0, "", 0.0], set(), set(), set()]
    ]
    
    all_calls = []
    bands_count = Counter()
    bands_odx = defaultdict(lambda: [0.0, ""])
    
    # Кэш для уже обработанных позывных
    call_cache = {}
    total_qsos = 0
    processed_files = 0
    
    for adif_file in file_list:
        processed_files += 1
        print(f"\n📁 Обрабатываю файл {processed_files}/{len(file_list)}: {os.path.basename(adif_file)}")
        
        try:
            with open(adif_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            qsos, header = adif_io.read_from_string(content)
            print(f"   Найдено QSO: {len(qsos)}")
        except Exception as e:
            print(f"   Ошибка чтения файла {adif_file}: {e}")
            continue
        
        file_qsos = 0
        for qso in qsos:
            file_qsos += 1
            total_qsos += 1
            
            if total_qsos % 100 == 0:
                print(f"   Обработано QSO: {total_qsos}...")
            
            full_call = qso.get('call', '').upper()
            if not full_call:
                continue
            
            base_call = get_base_call(full_call)
            all_calls.append(base_call)
            
            # Определяем диапазон
            band = qso.get('band', '').upper()
            if not band:
                freq = qso.get('freq', '')
                if freq:
                    try:
                        freq_mhz = float(freq)
                        if freq_mhz < 2: band = '160M'
                        elif freq_mhz < 4: band = '80M'
                        elif freq_mhz < 8: band = '40M'
                        elif freq_mhz < 15: band = '30M'
                        elif freq_mhz < 22: band = '20M'
                        elif freq_mhz < 25: band = '17M'
                        elif freq_mhz < 28: band = '15M'
                        elif freq_mhz < 30: band = '12M'
                        elif freq_mhz < 55: band = '10M'
                        else: band = '2M'
                    except:
                        band = 'Unknown'
                else:
                    band = 'Unknown'
            
            bands_count[band] += 1
            
            # Парсим мощность
            if power_override is not None:
                pwr = power_override
            else:
                pwr_val = qso.get('tx_pwr') or qso.get('power') or qso.get('app_rumlog_power')
                pwr = parse_power_custom(pwr_val)
            
            # Получаем локатор и страну
            loc = normalize_locator(qso.get('gridsquare', ''))
            country = qso.get('country', '') or qso.get('dxcc', '')
            
            # Если нет информации, ищем в интернете или библиотеке
            if (not loc or not country) and cic:
                if base_call in call_cache:
                    cached_loc, cached_country = call_cache[base_call]
                    if not loc and cached_loc:
                        loc = cached_loc
                    if not country and cached_country:
                        country = cached_country
                else:
                    new_loc, new_country = get_call_info(base_call, cic)
                    call_cache[base_call] = (new_loc, new_country)
                    if not loc and new_loc:
                        loc = new_loc
                    if not country and new_country:
                        country = new_country
            
            # Рассчитываем расстояние
            dist = 0.0
            if loc and my_loc_str and len(loc) >= 4 and len(my_loc_str) >= 4:
                try:
                    dist = float(locator.calculate_distance(my_loc_str, loc))
                except:
                    try:
                        dist = calculate_distance_approx(my_loc_str, loc)
                    except:
                        dist = 0.0
            
            # Обновляем ODX для диапазона
            if dist > bands_odx[band][0]:
                bands_odx[band] = [dist, full_call]
            
            # Обновляем статистику по категориям мощности
            for i in range(len(act_list)):
                if pwr <= act_list[i][1]:
                    act_list[i][2] += 1
                    if country:
                        act_list[i][4].add(str(country).upper())
                    if loc and len(loc) >= 2:
                        act_list[i][5].add(loc[:2])
                    if loc and len(loc) >= 4:
                        act_list[i][6].add(loc[:4])
                    if dist > act_list[i][3][0]:
                        act_list[i][3] = [dist, full_call, pwr]
        
        print(f"   ✅ Обработано QSO: {file_qsos}")
    
    # Записываем общую статистику в один файл
    print(f"\n💾 Записываю общую статистику в файл: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"ОБЩАЯ СТАТИСТИКА ПО ВСЕМ ADIF ФАЙЛАМ\n")
        f.write(f"Дата анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Количество проанализированных файлов: {len(file_list)}\n")
        f.write(f"Общее количество QSO: {total_qsos}\n")
        f.write(f"Ваш локатор: {my_loc_str}\n")
        f.write("=" * 80 + "\n\n")
        
        for item in act_list:
            name, max_pwr, count, odx, countries, fields, squares = item
            
            # Форматируем вывод мощности
            if name == "ALL":
                power_display = "все мощности"
            elif name == "QRPu":
                power_display = f"{max_pwr * 1000:.0f} мВт"
            elif name == "QRP-X":
                power_display = f"{max_pwr * 1000:.0f} мВт"
            else:
                power_display = f"{max_pwr} Ватт"
            
            if name == "ALL":
                f.write(f"📡 ОБЩАЯ СТАТИСТИКА ПО ВСЕМ СВЯЗЯМ ({power_display})\n")
            else:
                f.write(f"📡 СТАТИСТИКА ПО {name}-СВЯЗЯМ (до {power_display} включительно)\n")
            f.write("-" * 60 + "\n")
            f.write(f"   • Количество {name}-связей: {count}\n")
            
            if odx[0] > 0:
                if odx[2] < 0.01:
                    pwr_display = f"{odx[2] * 1000:.2f} мВт"
                elif odx[2] < 1:
                    pwr_display = f"{odx[2] * 1000:.0f} мВт"
                else:
                    pwr_display = f"{odx[2]:.1f} Вт"
                f.write(f"   • ODX самая дальняя связь: {odx[1]}\n")
                f.write(f"     └─ Расстояние: {odx[0]:.1f} км, мощность: {pwr_display}\n")
            else:
                f.write(f"   • ODX самая дальняя связь: -\n")
            
            f.write(f"   • Количество сработанных стран (WKD countries): {len(countries)}\n")
            f.write(f"   • Количество сработано полей (WKD fields): {len(fields)}\n")
            f.write(f"   • Количество сработано квадратов (WKD squares): {len(squares)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("🏆 ТОП-20 САМЫХ ЧАСТЫХ ПОЗЫВНЫХ (ОБЩАЯ СТАТИСТИКА)\n")
        f.write("-" * 60 + "\n")
        top_20 = Counter(all_calls).most_common(20)
        for i, (c, cnt) in enumerate(top_20, 1):
            f.write(f"   {i:2}. {c:15} → {cnt:3} раз(а)\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("📻 СТАТИСТИКА ПО ДИАПАЗОНАМ (С ODX)\n")
        f.write("-" * 60 + "\n")
        
        # Выводим диапазоны в определенном порядке
        band_order = ['160M', '80M', '40M', '30M', '20M', '17M', '15M', '12M', '10M', '6M', '2M', '70CM', 'Unknown']
        for b in band_order:
            if b in bands_count:
                cnt = bands_count[b]
                dist_val, call_val = bands_odx[b]
                if dist_val > 0:
                    f.write(f"   • {b:6} → {cnt:4} связей. ODX: {call_val:12} ({dist_val:.1f} км)\n")
                else:
                    f.write(f"   • {b:6} → {cnt:4} связей. ODX: -\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("📊 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ\n")
        f.write("-" * 60 + "\n")
        f.write(f"   • Всего уникальных позывных: {len(set(all_calls))}\n")
        f.write(f"   • Среднее количество QSO на позывной: {total_qsos / len(set(all_calls)):.1f}\n")
        
        # Информация об обработанных файлах
        f.write(f"\n   📁 Обработанные файлы:\n")
        for fname in file_list:
            f.write(f"      - {os.path.basename(fname)}\n")
    
    print(f"\n" + "=" * 60)
    print(f"✅ АНАЛИЗ ЗАВЕРШЕН!")
    print(f"📄 Результаты сохранены в: {output_file}")
    print("=" * 60)
    
    # Краткий отчет в консоли
    print(f"\n📊 КРАТКИЙ ОТЧЕТ:")
    for item in act_list:
        name, max_pwr, count, odx, countries, fields, squares = item
        if count > 0:
            label = "Все связи" if name == "ALL" else name
            print(f"   {label}: {count} связей, {len(countries)} стран, {len(fields)} полей, {len(squares)} квадратов")
            if odx[0] > 0:
                print(f"      └─ Дальняя: {odx[0]:.1f} км")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("ADIF АНАЛИЗАТОР - ОБЪЕДИНЕННАЯ СТАТИСТИКА")
        print("=" * 60)
        print("\nИспользование:")
        print("  python main_analysis.py <файл.adif> [локатор]")
        print("  python main_analysis.py <папка> [локатор]")
        print("\nПримеры:")
        print("  python main_analysis.py log.adi LO48VI")
        print("  python main_analysis.py /путь/к/папке/ LO48VI")
        print("\nКатегории мощности:")
        print("  • QRP   - до 5 Вт")
        print("  • QRPp  - до 1 Вт")
        print("  • QRP-X - до 0.1 Вт (100 мВт)")
        print("  • QRPu  - до 0.01 Вт (10 мВт)")
        print("=" * 60)
        sys.exit(1)
    
    adif_path = sys.argv[1]
    my_loc = sys.argv[2] if len(sys.argv) > 2 else "LO48VI"
    
    # Собираем список файлов
    if os.path.isdir(adif_path):
        files = [os.path.join(adif_path, f) for f in os.listdir(adif_path) 
                if f.lower().endswith(('.adi', '.adif'))]
        if not files:
            print(f"❌ В папке {adif_path} нет ADIF файлов")
            sys.exit(1)
        # Создаем общий выходной файл для всех файлов в папке
        output_file = os.path.join(adif_path, f"combined_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    else:
        files = [adif_path]
        # Создаем выходной файл в той же папке, что и исходный
        output_file = os.path.splitext(adif_path)[0] + "_stats.txt"
    
    print(f"\n📂 Найдено файлов для анализа: {len(files)}")
    for f in files:
        print(f"   - {os.path.basename(f)}")
    
    analyze_files(files, my_loc.upper(), output_file)