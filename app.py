import streamlit as st
from google import genai
from google.genai import types
import cloudscraper
from bs4 import BeautifulSoup
import time

# Настройка страницы
st.set_page_config(page_title="HH Hunter Oracle", layout="centered")


# --- Блок логики парсинга ---
def extract_clean_text(url):
    """Извлекает полезную нагрузку с веб-страницы, имитируя браузер."""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    try:
        # Добавляем задержку, чтобы не выглядеть как агрессивный бот
        time.sleep(1)
        response = scraper.get(url)

        if response.status_code != 200:
            return f"Ошибка: HH.ru вернул статус {response.status_code}. Возможно, сработала защита."

        soup = BeautifulSoup(response.text, 'html.parser')

        # Удаляем визуальный шум
        for element in soup(["script", "style", "header", "footer", "nav"]):
            element.decompose()

        # Мы ищем основные блоки: описание вакансии или тело резюме
        # На HH обычно это классы вроде 'vacancy-description' или 'resume-wrapper'
        # Но возьмем текст из основного контейнера для универсальности
        main_content = soup.find('main') or soup.find('div', {'id': 'common-pading'}) or soup.body

        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)

        return text[:15000]  # Ограничение, чтобы не раздувать контекст
    except Exception as e:
        return f"Критический сбой парсера: {str(e)}"


# --- Интерфейс Streamlit ---
st.title("⚖️ HH.ru Pre-scoring Oracle")
st.caption("Пока ты созерцаешь вечность, алгоритм сопоставляет ссылки.")

with st.sidebar:
    st.header("Настройки")
    api_key = st.text_input("Gemini API Key", type="password", help="Получите ключ в Google AI Studio")
    st.info(
        "Внимание: для доступа к полным резюме ваш браузерный сеанс должен быть авторизован как 'Работодатель'. Этот парсер работает с публичными данными.")

vac_url = st.text_input("URL Вакансии на hh.ru")
res_url = st.text_input("URL Резюме на hh.ru")

system_instruction = (
    """Проскорь кандидата по степени соответствия вакансии.

Сначала составь краткий аналитический комментарий, объясняющий твою оценку.

Оцени качество резюме по шкале от 1 до 10. Обрати внимание на следующее:
- Понятно ли, с какими задачами и проблемами сталкивался кандидат?
- Описано ли, как именно он их решал?
- Указаны ли результаты и достижения?
- Насколько тщательно оформлено резюме и видно ли, что кандидат умеет анализировать своё влияние на компанию?

Затем представь итоговую оценку соответствия кандидата — по шкале от 1 до 10.
Эта оценка должна основываться в том числе на качестве резюме."""
)

if st.button("Провести анализ"):
    if not api_key:
        st.error("Без ключа Gemini я — просто набор символов.")
    elif not vac_url or not res_url:
        st.warning("Пришли обе ссылки, иначе сопоставление невозможно.")
    else:
        client = genai.Client(api_key=api_key)

        with st.status("Работаем с данными...", expanded=True) as status:
            st.write("Парсим вакансию...")
            vacancy_raw = extract_clean_text(vac_url)

            st.write("Парсим резюме...")
            resume_raw = extract_clean_text(res_url)

            status.update(label="Данные получены. Опрашиваем нейросеть...", state="running")

            prompt = f"ВАКАНСИЯ:\n{vacancy_raw}\n\nРЕЗЮМЕ:\n{resume_raw}"

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.4
                    )
                )
                status.update(label="Анализ завершен!", state="complete")

                st.subheader("Вердикт HR-Оракула")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"Ошибка LLM: {e}")

# --- Предложение по улучшению ---
st.divider()
with st.expander("Что можно улучшить? (Советы для продвинутых)"):
    st.markdown("""
    * **Обход авторизации:** Если резюме скрыто от неавторизованных пользователей, парсер увидит только окно логина. Нужно передавать `cookies` от твоего аккаунта работодателя в `scraper.get()`.
    * **Использование Proxy:** Чтобы HH не забанил твой IP после 10-го запроса, стоит использовать ротационные прокси.
    * **Markdown отчет:** Можно добавить кнопку 'Скачать отчет в PDF', чтобы прикреплять мнение нейросети к делу кандидата.
    """)
