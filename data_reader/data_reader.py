import paho.mqtt.client as paho
import psycopg2
import time
import json

# Configurações paho
client = paho.Client(paho.CallbackAPIVersion.VERSION2)
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

       comando_coleta = """
           SELECT id, atributos FROM api.coleta WHERE dispositivo_id = %s AND status = True;
       """

       comando_token = """
           SELECT token FROM api.dispositivo WHERE id = %s;
       """

       comando_status = """
           SELECT ativo FROM api.dispositivo WHERE id = %s;
       """
       cursor.execute(comando_token, (dispositivo_id,))
       token = cursor.fetchone()
       if token:
           dispositivo_token = token[0]
           if usuario_token == dispositivo_token:
               cursor.execute(comando_status, (dispositivo_id,))
               dispositivo_status = cursor.fetchone()[0]
               if dispositivo_status == True:
                   cursor.execute(comando_coleta, (dispositivo_id,))
                   coleta = cursor.fetchone()
                   payload_data.pop()
                   payload_data.pop(0)
                   fields = ', '.join([f'a{i+1}' for i in range(len(payload_data))])
                   values = ', '.join(['%s'] * (len(payload_data)))
                   if coleta:
                       coleta_id = coleta[0]
                       atributos = []

                       if coleta[1]: 
                           string=coleta[1][0]
                           lista = json.loads(string) 
                           for item in lista:
                               atributos.append(item)

                       if len(payload_data) == len(atributos):
                           comando_inserir_coleta = f"""
                           INSERT INTO api.dados_coleta_{coleta_id} ({fields})
                           VALUES ({values});
                           """
                           cursor.execute(comando_inserir_coleta, (payload_data))
                           conn.commit()
                           #print(comando_inserir_coleta, (payload_data))
                           client.publish(f"valores/{dispositivo_id}", payload=f"2 + {payload_data[0]}", qos=1) 
                           print("Dados inseridos com sucesso no banco de dados!")
                           #time.sleep(0.1)

                       else:
                           comando_inserir_dispositivo = f"""
                           INSERT INTO api.dados_dispositivo_{dispositivo_id} ({fields})
                           VALUES ({values});
                           """
                           cursor.execute(comando_inserir_dispositivo, (payload_data))
                           conn.commit()
                           #print(comando_inserir_dispositivo, (payload_data))
                           client.publish(f"valores/{dispositivo_id}", payload=f"8 + {payload_data[0]}", qos=1) 
                           print("Quantidade de atributos não conferem. Dados inseridos na tabela de backup do dispositivo.")
                   else:

                       comando_inserir_dispositivo = f"""
                       INSERT INTO api.dados_dispositivo_{dispositivo_id} ({fields})
                       VALUES ({values});
                       """
                       cursor.execute(comando_inserir_dispositivo, (payload_data))
                       conn.commit()
                       print(comando_inserir_dispositivo, (payload_data))
                       client.publish(f"valores/{dispositivo_id}", payload=f"7 + {payload_data[1]}", qos=1)
                       print("Nenhuma coleta aberta. Dados inseridos na tabela de backup do dispositivo.")
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
   print(f'Subscribed: mid = {mid} | granted_qos = {granted_qos}.')

"""def on_disconnect(cliente, userdata, rc, flags):
   if rc != 0:
       print(f'Desconectado inesperadamente, tentando reconectar...')
       client.reconnect()
       client.disconnect()
       time.sleep(3)
       verify()"""

def on_message(client, userdata, msg: paho.MQTTMessage):
   if not msg.retain:
       actual_payload = msg.payload.decode('utf-8').split(';')
       insertPayloadPostgres(actual_payload)
       print(actual_payload)
   else:
       print('mensagem retida ' + msg.payload.decode('utf-8'))

def verify():
   print(client.is_connected)
   while client.is_connected:
           try:
                client.disconnect
                client.tls_set()
                client.username_pw_set(client_username, client_password)
                client.connect(broker_address, broker_port)
                client.subscribe('valores', qos=0)
                time.sleep(5)
                client.loop_forever()
           except KeyboardInterrupt:
               print('Encerrando pelo console...')
               client.disconnect()
               break
           except Exception as e:
               print(f'Erro: {e}. Tentando reconectar em 5 segundos...')
               time.sleep(5)   

def main():
   client.on_connect = on_connect
   client.on_subscribe = on_subscribe
   client.on_message = on_message
   #client.on_disconnect = on_disconnect

   verify()



if __name__ == '__main__':
   main()