import paho.mqtt.client as paho
import psycopg2
import time


# Configurações paho
client = paho.Client(client_id = 'data_reader', userdata = None, protocol = paho.MQTTv5)
client_username = 'redes1'
client_password = 'projetoredes1'
broker_address = '80fe29ce8268427c9a4a9aeb6cabf603.s2.eu.hivemq.cloud'
broker_port = 8883

# Configurações psycopg2
DB_HOST = "localhost"
#DB_HOST = "10.0.2.15"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "mysecretpassword"
DB_PORT = "5433"


def insertPayloadPostgres(payload_data):
    # Se conectar ao banco de dados
    conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )
    cursor = conn.cursor()

    # Inserir os dados na tabela
    try:
        # Construa a parte variável do comando SQL
        fields = ', '.join([f'a{i+1}' for i in range((len(payload_data)-1))])
        values = ', '.join(['%s'] * (len(payload_data)-1))

        comando = f"""
            INSERT INTO api.coleta (dispositivo_id, {fields})
            VALUES (%s, {values});
        """
        print(comando)
        
        cursor.execute(comando, payload_data)
        conn.commit()
        print("Dados inseridos com sucesso no banco de dados!")
    except psycopg2.Error as e:
        print(f"Erro ao inserir dados: {e}")
    finally:
        cursor.close()
        
def on_connect(client, userdata, flags, rc, properties = None):
    print(f'CONNACK received with code {rc}.')

def on_subscribe(client, userdata, mid, granted_qos, properties = None):
    print(f'Subscribed: mid = {mid}  | granted_qos = {granted_qos}.')

def on_disconnect(client, userdata, rc, flags):
    if rc != 0:
        print(f'Desconectado inesperadamente, tentando reconectar...')
        client.reconnect()

def on_message(client, userdata, msg: paho.MQTTMessage):
    if not msg.retain:
        #file = open('com_sensor_ambiente/app/valores.csv', 'a')
        #file.write(f"{msg.payload.decode('utf-8')}\n")
        #file.close()

        actual_payload = msg.payload.decode('utf-8').split(';')
        insertPayloadPostgres(actual_payload)
        print(actual_payload)
    else:
        print('mensagem retida ' + msg.payload.decode('utf-8'))

def main():
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.tls_set()
    client.username_pw_set(client_username, client_password)

    while True:
        try:
            client.connect(broker_address, broker_port)
            client.subscribe('valores', qos=0)
            client.loop_forever()
        except KeyboardInterrupt:
            print('Encerrando...')
            client.disconnect()
            break
        except Exception as e:
            print(f'Erro: {e}. Tentando reconectar em 5 segundos...')
            time.sleep(5)

if __name__ == '__main__':
    main()