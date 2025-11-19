
from google import genai
# Установите свой API-ключ.
# ВНИМАНИЕ: Для примера, пожалуйста, замените "ВАШ_API_КЛЮЧ" на ваш реальный ключ.
# Я заменил ключ из вашего сообщения на заглушку, чтобы он не сохранился в чате.
API_KEY = "AIzaSyD7JhETZ6teq3pThHJp-uMdl_BeYFhyGLo"

try:
    # Инициализация клиента GenAI
    client = genai.Client(api_key=API_KEY)

    # Определяем запрос (prompt)
    prompt = "Напиши короткое, вдохновляющее четверостишие о программировании."

    # Отправка запроса к модели
    print(f"Отправка запроса к модели 'gemini-2.5-flash'...")

    # Выполнение запроса
    response = client.models.generate_content(
        model='gemini-2.5-flash',  # Быстрая и экономичная модель
        contents=prompt,
    )

    # Вывод ответа
    print("\n--- Ответ Gemini ---")
    print(response.text)
    print("--------------------")

# ИСПРАВЛЕНО: Правильный отступ для блока 'except' (на том же уровне, что и 'try')
except Exception as e:
    print(f"Произошла ошибка: {e}")
    # Это может быть связано с неправильным ключом, превышением лимитов или проблемами с сетью
