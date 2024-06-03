import paho.mqtt.client as paho
import psycopg2
import time


# Configurações paho
client = paho.Client(client_id = 'data_reader', userdata = None, protocol = paho.MQTTv5)
client_username = 'redes1'
client_password = 'projetoredes1'
broker_address = '80fe29ce8268427c9a4a9aeb6cabf603.s2.eu.hivemq.cloud'
broker_port = 8883

# Configurações postgresql
DB_HOST = "localhost"
#DB_HOST = "10.0.2.15"
DB_NAME = "farmscihub"
DB_USER = "farmscihub_admin"
DB_PASS = "pibiti.fsh.2010"
DB_PORT = "5433"

def insertPayloadPostgres(payload_data):

    dispositivo_id = payload_data[0]
    usuario_token = payload_data[-1] 
    
    try:
        
        conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )
        cursor = conn.cursor()

        comando_token = """
            SELECT token FROM api.dispositivo WHERE id = %s;
        """
        
        comando_status = """
            SELECT ativo FROM api.dispositivo WHERE id = %s;
        """
        cursor.execute(comando_token, (dispositivo_id,))
        existe = cursor.fetchone()
        if existe:
            dispositivo_token = existe[0]
            if usuario_token == dispositivo_token:
                cursor.execute(comando_status, (dispositivo_id,))
                dispositivo_status = cursor.fetchone()[0]
                if dispositivo_status == True:
                    fields = ', '.join([f'a{i+1}' for i in range((len(payload_data)-1))])
                    values = ', '.join(['%s'] * (len(payload_data)-1))

                    comando_inserir = f"""
                        INSERT INTO api.coleta (dispositivo_id, {fields})
                        VALUES (%s, {values});
                    """
                    cursor.execute(comando_inserir, payload_data)
                    conn.commit()
                    print("Dados inseridos com sucesso no banco de dados!")
                    client.publish(f"valores/{dispositivo_id}", payload=f"2 + {payload_data[1]}", qos=1)
                else:
                    client.publish(f"valores/{dispositivo_id}", payload=f"6 + {payload_data[1]}", qos=1)
                    print("Dispositivo desabilitado. Dados não inseridos.")
            else:
                client.publish(f"valores/{dispositivo_id}", payload=f"4 + {payload_data[1]}", qos=1)
                print("Token do usuário não corresponde ao token do dispositivo. Dados não inseridos.")
        else:
            client.publish(f"valores/{dispositivo_id}", payload=f"3 + {payload_data[1]}", qos=1)
            print("ID informado pelo usuário não corresponde ao ID de nenhum dispositivo. Dados não inseridos.")
    except psycopg2.Error as e:
        client.publish(f"valores/{dispositivo_id}", payload=f"5 + {payload_data[1]}", qos=1)
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
        #client.publish(f"valores/{actual_payload[0]}", payload="1", qos=1)
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