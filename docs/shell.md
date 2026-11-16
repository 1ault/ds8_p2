cd C:\Users\Usuario\code\iot\Parcial2_IoT_Seguridad

==================================

Backend + SQL local (paso a paso):

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m backend.main --seed

http://127.0.0.1:8000

admin 
seguridad2026

==================================

SQL:

python -m backend.cli resumen
python -m backend.cli historico --horas 24 --limite 10
python -m backend.cli eventos
python -m backend.cli comandos
python -m backend.cli estadisticas

del data\centinela.db*
python -m backend.main --seed

==================================


zed:

C:\Users\Usuario\code\iot\Parcial2_IoT_Seguridad\entregables\Wokwi_Centinela_IoT


çtrl + a o ctrl + c

.bat

python -m mpremote connect port:rfc2217://localhost:4000 fs cp main.py :main.py





https://thingspeak.mathworks.com/channels/3581298/api_keys
.env
3581298
6D2D0FF4O42VFUU3


cd C:\Users\Usuario\code\iot\Parcial2_IoT_Seguridad
venv\Scripts\activate
python -m backend.main --seed
