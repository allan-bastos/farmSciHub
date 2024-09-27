from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file, abort, session, make_response
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
import pyrebase
import psycopg2 #pip install psycopg2 
import psycopg2.extras
from werkzeug.utils import secure_filename
import os
import json
import matplotlib
import matplotlib.ticker as ticker
matplotlib.use('Agg')
from functools import wraps
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
from threading import Thread
import pandas as pd
import requests
import shutil
import io
import firebase_admin
from firebase_admin import credentials, auth 

# Inicializa o aplicativo Firebase
cred = credentials.Certificate('./app/static/farmscihub-credentials.json') 
firebase_admin.initialize_app(cred)


from jinja2 import Template

# config firebase

firebaseConfig = {
    'apiKey': "AIzaSyDS9PwNH2sEB1kZ8-BHFSXQo7yCIPRzFOU",
    'authDomain': "farmscihub-5a778.firebaseapp.com",
    'projectId': "farmscihub-5a778",
    'storageBucket': "farmscihub-5a778.appspot.com",
    'messagingSenderId': "1064882604925",
    'appId': "1:1064882604925:web:ec349318593226d2301a14",
    'measurementId': "G-NJ5DYY90JQ",
    'databaseURL': ""
}

firebase = pyrebase.initialize_app(firebaseConfig)
authP = firebase.auth()




# Configurações postgresql
DB_HOST = "localhost"
#DB_HOST = "10.0.2.15"
DB_NAME = "farmscihub"
DB_USER = "farmscihub_admin"
DB_PASS = "pibiti.fsh.2010"
DB_PORT = "5433"


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3'}
 
conn = psycopg2.connect(
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

app = Flask(__name__)
app.secret_key = 'chave_secreta'


UPLOAD_FOLDER = './app/static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, nome, senha, nome_completo, vinculo, acessos, email, firebase_id, v_email, isAdmin, permissoes):
        self.id = id
        self.nome = nome
        self.senha = senha
        self.email = email
        self.nome_completo = nome_completo
        self.vinculo = vinculo
        self.acessos = acessos
        self.permissoes = permissoes
        self.firebase_id = firebase_id
        self.v_email = v_email
        self.isAdmin = isAdmin
        
@login_manager.user_loader
def load_user(user_id):
    cur = conn.cursor()
    cur.execute("SELECT id, nome, senha, nome_completo, vinculo, acessos, email, firebase_id, v_email, admin FROM local.usuario WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    print(user_data)
    if user_data:
        cur.execute(""" SELECT experimento_id, p_experimento, exp_anexos, p_etapas, etp_anexos, p_dispositivos
                        FROM local.permissoes
                        WHERE usuario_id = %s
                        AND (fim IS NULL OR fim > CURRENT_DATE);
                        """, (user_id,))
        permissions_data = cur.fetchall()
        print(permissions_data)
        user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5], user_data[6], user_data[7], user_data[8], user_data[9],permissions_data)
        
        
        return user
    else:
        return None

def get_folder_size(path):
  total_size = 0
  for dirpath, _, filenames in os.walk(path):
    for filename in filenames:
      file_path = os.path.join(dirpath, filename)
      total_size += os.path.getsize(file_path)
  return total_size


def email_verificado_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            try:
                if not current_user.v_email:
                    return redirect(url_for('verificacao_email'))
            except Exception as e:
                print(f"Erro ao verificar email no Firebase: {e}")
                return redirect(url_for('verificar_email'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function1(*args, **kwargs):
        if current_user.is_authenticated:
            try:
                if not current_user.isAdmin:
                    return redirect(url_for('acesso_negado'))
            except Exception as e:
                print(f"Erro ao verificar admin: {e}")
                return redirect(url_for('acesso_negado'))
        return f(*args, **kwargs)
    return decorated_function1

@app.route('/')
def index():    
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    s = "SELECT * FROM api.experimento;"
    cur.execute(s)
    list_exps = cur.fetchall()
    for exp in list_exps:
        exp['criado_em'] = exp['criado_em'].strftime('%Y-%m-%d %H:%M:%S')
    print(list_exps)
    return render_template('index.html', experimentos=list_exps, user=current_user)

@app.route('/sobre')
def sobre():
    return render_template('sobre.html', user=current_user)


@app.template_filter('get_permissao')
def get_permissao(permissoes, experimento_id):
    for permissao in permissoes:
        if permissao.get('experimento_id') == experimento_id:
            return permissao
    return None

app.jinja_env.filters['get_permissao'] = get_permissao

#------------------------------------------------------------USUÁRIO---------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------
@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'GET':
        return render_template('recuperar_senha.html', user=current_user)

    elif request.method == 'POST':
        email = request.form['email']
        
        try:
            authP.send_password_reset_email(email)
            print("Instruções para redefinir sua senha foram enviadas para o seu e-mail.")
            return redirect(url_for('login')) 
        except Exception as e:
            print(f"Erro ao enviar e-mail de redefinição de senha: {e}")
            message = "Erro ao tentar enviar o e-mail de recuperação. Verifique se o e-mail está correto e tente novamente."
            print(message)
            return render_template('recuperar_senha.html', user=current_user, message=message)

@app.route('/acesso_negado', methods=['GET'])
@login_required
def acesso_negado():
    if request.method == 'GET':
        return render_template('acesso_negado.html', user=current_user)

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'GET':
        user_id = current_user.id
        nome = current_user.nome
        senha = current_user.senha
        email = current_user.email
        nome_completo = current_user.nome_completo
        vinculo = current_user.vinculo
        email_verified = current_user.v_email
        return render_template('perfil.html', user_id=user_id, nome=nome, senha=senha, nome_completo=nome_completo, vinculo=vinculo, email=email, email_verified=email_verified, user=current_user)

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    try:
        authP.current_user = None
        print("Usuário deslogado no Firebase.")
    except Exception as e:
        print(f"Erro ao deslogar no Firebase: {e}")
    logout_user() 
    print('Você saiu com sucesso.')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'GET':
        return render_template('login.html', user=current_user)
    elif request.method == 'POST':
        email = request.form['email']
        senha = request.form['password']
        try:
            userf = authP.sign_in_with_email_and_password(email, senha)
            userf = authP.refresh(userf['refreshToken'])
            
            user_info = authP.get_account_info(userf['idToken'])
            email_verified = user_info['users'][0]['emailVerified']
            print(email_verified)

            cur = conn.cursor()
            cur.execute("SELECT id FROM local.usuario WHERE email = %s", (email,))
            user_id = cur.fetchone()

            if user_id:
                cur = conn.cursor()
                cur.execute("UPDATE local.usuario set firebase_id = %s, v_email = %s WHERE id = %s", (userf['idToken'], email_verified, user_id[0]))
                conn.commit()

                user = load_user(user_id[0]) 
                login_user(user)
                return redirect(url_for('perfil', user=current_user))
            else:
                message = "Email não encontrado no sistema."

        except Exception as e:
            print(f"Erro durante o processo de login: {e}")
            message = "Credenciais inválidas. Tente novamente." 

    return render_template("login.html", message=message, user=current_user)



@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('cadastro.html', user=current_user)

    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        nome_completo = request.form['nome_completo']
        vinculo = request.form['vinculo']
        email = request.form['email']

        domain = email.split('@')[-1]

    
        with conn.cursor() as cur:
            cur.execute("SELECT dominio FROM local.dominios")
            allowed_domains = [row[0] for row in cur.fetchall()] 
            print(allowed_domains)

        if domain not in allowed_domains:
            message = "O registro é permitido apenas para domínios específicos."
            return render_template('cadastro.html', user=current_user, message=message)

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM local.usuario WHERE email = %s", (email,))
            user_obj = cur.fetchone()

            if user_obj:
                message = "Este email já está registrado. Por favor, utilize outro."
                return render_template('cadastro.html', user=current_user, message=message)

            user = authP.create_user_with_email_and_password(email, senha)
            authP.send_email_verification(user['idToken'])
            cur.execute("INSERT INTO local.usuario (nome, senha, nome_completo, vinculo, email) VALUES (%s, %s, %s, %s, %s)", (nome, senha, nome_completo, vinculo, email))
            conn.commit()

        return redirect(url_for('login', user=current_user))


@app.route('/verificar_email', methods=['GET', 'POST'])
@login_required
def verificar_email():
    if request.method == 'GET':
        return render_template('verificar_email.html', user=current_user)
    
    elif request.method == 'POST':
        try:
            # Reenviar email de verificação
            authP.send_email_verification(current_user.firebase_token)
            message = "Email de verificação reenviado. Por favor, cheque sua caixa de entrada."
        except Exception as e:
            message = f"Erro ao reenviar email de verificação: {e}"
        
        return render_template('verificar_email.html', message=message, user=current_user)
    


@app.route('/editar-perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    if request.method == 'GET':
        nome = current_user.nome
        nome_completo = current_user.nome_completo
        vinculo = current_user.vinculo
        return render_template('perfil-editar.html', nome=nome, nome_completo=nome_completo, vinculo=vinculo, user=current_user)
    
    elif request.method == 'POST':
        nome = request.form['username']
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        nome_completo = request.form['nome_completo']
        vinculo = request.form['vinculo']

        cur = conn.cursor()
        cur.execute("UPDATE local.usuario SET nome=%s, nome_completo=%s, vinculo=%s WHERE id=%s", (nome, nome_completo, vinculo, current_user.id))
        conn.commit()
        message = "Perfil alterado com sucesso."

        try:
            if nova_senha:
                user = auth.get_user_by_email(current_user.email)
                auth.update_user(
                    user.uid,
                    password=nova_senha
                )
                message = "Senha e/ou perfil alterados com sucesso."
        except Exception as e:
            print(f"Erro ao alterar a senha: {e}")
            message = "Erro ao tentar alterar senha e/ou perfil. Tente novamente."

        return render_template('perfil-editar.html', nome=nome, nome_completo=nome_completo, vinculo=vinculo, user=current_user, message=message)

@app.route('/resetar-senha', methods=['GET'])
@login_required
def resetar_senha():
    try:
        authP.send_password_reset_email(current_user.email)
        message = "Um e-mail foi enviado para redefinir sua senha."
        print(message)
    except Exception as e:
        print(f"Erro ao enviar e-mail de redefinição: {e}")
        message = "Erro ao tentar enviar o e-mail de redefinição. Tente novamente."
        print(message)

    return redirect(url_for('editar_perfil', user=current_user))


    
@app.route('/deletar-perfil', methods=['GET'])
@login_required
def deletar_perfil():
    try:
        # URL para deletar o usuário
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:delete?key={firebaseConfig['apiKey']}"

        # Dados necessários para deletar o usuário
        data = {
            "idToken": current_user.firebase_id  # Usando o token de autenticação do usuário
        }

        # Fazer a requisição para deletar o usuário no Firebase
        response = requests.post(url, json=data)

        if response.status_code == 200:
            cur = conn.cursor()
            cur.execute("""UPDATE api.experimento
                SET disponivel_para = array_remove(disponivel_para, %s);
                """, (current_user.id,))
            conn.commit()

            cur.execute("DELETE FROM local.usuario WHERE id=%s", (current_user.id,))
            conn.commit()

            return redirect(url_for('logout', user=current_user))
        else:
            print(f"Erro ao deletar usuário no Firebase: {response.json()}")
            flash('Erro ao deletar perfil no Firebase.', 'danger')
            return redirect(url_for('perfil', user=current_user))

    except Exception as e:
        print(f"Erro ao deletar usuário: {e}")
        flash('Erro ao deletar perfil.', 'danger')
        return redirect(url_for('perfil', user=current_user))





#-------------------------------------------COMPARTILHAMENTO/FORMULARIO---------------------------------------------------------------------
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

@app.route('/compartilhados_experimento/<int:experimento_id>')
@login_required
@email_verificado_required
def compartilhamento_experimento(experimento_id):
    usuarios=[]
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT disponivel_para FROM api.experimento WHERE id = %s", (experimento_id,))
    usuarios_ids = cur.fetchone()
    
    if usuarios_ids:
        for usuario_id in usuarios_ids['disponivel_para']:
            cur.execute("SELECT * FROM local.usuario WHERE id = %s", (usuario_id,))
            usuario = cur.fetchone()
            usuarios.append(usuario)
            
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) FROM local.solicitacoes WHERE experimento_id = %s AND status='aguardando'", (experimento_id,))
    count_solicitacoes = cur.fetchone()[0]
    
    return render_template('experimento-compartilhado.html', usuarios=usuarios, experimento_id=experimento_id, count_solicitacoes=count_solicitacoes,experimento=experimento,user=current_user)



@app.route('/solicitacoes_experimento/<int:experimento_id>')
@login_required
@email_verificado_required
def solicitacoes_experimento(experimento_id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM local.solicitacoes WHERE experimento_id = %s AND status= 'aguardando' ORDER BY data_hora DESC;", (experimento_id,))
    solicitacoes = cur.fetchall()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('experimento-solicitacoes.html', solicitacoes=solicitacoes, experimento_id = experimento_id, experimento=experimento, user=current_user)


@app.route('/historico-solicitacoes-experimento/<int:experimento_id>/<int:usuario_id>/')
@login_required
@email_verificado_required
def historico_solicitacoes_experimento(experimento_id, usuario_id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM local.solicitacoes WHERE experimento_id = %s AND solicitante_id = %s ORDER BY data_hora DESC;", (experimento_id, usuario_id))
    solicitacoes = cur.fetchall()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    cur.execute("SELECT * FROM local.usuario WHERE id = %s", (usuario_id,))
    usuario = cur.fetchone()
    
    return render_template('experimento-solicitacoes-historico.html', solicitacoes=solicitacoes, experimento_id = experimento_id, experimento=experimento, usuario=usuario, user=current_user)

@app.route('/<int:experimento_id>/recusar-solicitacao/<int:solicitacao_id>')
@login_required
@email_verificado_required
def recusar_solicitacao(experimento_id, solicitacao_id):
    cur = conn.cursor()
    cur.execute("UPDATE local.solicitacoes SET status='recusada' WHERE id = %s", (solicitacao_id,))
    conn.commit()
    return redirect(url_for('solicitacoes_experimento',  user=current_user, experimento_id=experimento_id))

@app.route('/aceitar-solicitacao/<int:id>')
@login_required
@email_verificado_required
def aceitar_solicitacao(id):
    cur = conn.cursor()
    cur.execute("SELECT experimento_id, solicitante_id, criador_experimento_id FROM local.solicitacoes WHERE id = %s", (id,))
    result = cur.fetchone()
    experimento_id = result[0]
    solicitante_id = result[1]

    cur = conn.cursor()
    cur.execute("SELECT solicitacao_id FROM local.permissoes WHERE usuario_id = %s AND experimento_id = %s", (solicitante_id, experimento_id))
    existe = cur.fetchone()
    if not existe:
        cur.execute("""INSERT INTO local.permissoes (solicitacao_id, usuario_id, experimento_id, p_experimento, p_etapas, p_dispositivos, inicio, fim)
        VALUES (%s, %s, %s, 'leitura', 'nenhuma', 'nenhuma', CURRENT_DATE, NULL);""", (id, solicitante_id, experimento_id))
        conn.commit()
        
        cur.execute("UPDATE local.usuario SET acessos = array_append(acessos, %s) WHERE id = %s", (experimento_id, solicitante_id))
        conn.commit()
        
        cur.execute("UPDATE api.experimento SET disponivel_para = array_append(disponivel_para, %s) WHERE id = %s", (solicitante_id, experimento_id))
        conn.commit()
        
    else:
        cur.execute("""UPDATE local.solicitacoes SET status = 'sobrescrita' WHERE id=%s""", (existe[0],))
        conn.commit()
        
        cur.execute("""UPDATE local.permissoes SET solicitacao_id = %s WHERE usuario_id = %s AND experimento_id = %s""", (id,solicitante_id, experimento_id))
        conn.commit()
    
    print(f"UPDATE FEITO exp{experimento_id} e user{solicitante_id}")
    cur.execute("UPDATE local.solicitacoes SET status='aceita' WHERE id = %s", (id,))
    conn.commit()
    return redirect(url_for('cadastrar_permissoes', user=current_user, experimento_id = experimento_id, usuario_id = solicitante_id))

@app.route('/detalhes-experimento/<int:experimento_id>/permissao/<int:usuario_id>', methods=['POST', 'GET'])
@login_required
@email_verificado_required
def cadastrar_permissoes(experimento_id, usuario_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM local.usuario WHERE id = %s", (usuario_id,))
    colaborador = cur.fetchone()
    
    cur = conn.cursor()
    cur.execute("SELECT p_experimento, p_etapas, p_dispositivos, exp_anexos, etp_anexos, fim FROM local.permissoes WHERE usuario_id = %s AND experimento_id = %s", (usuario_id, experimento_id))
    permissao = cur.fetchone()

    data_atual = date.today()
    
    if request.method == 'POST':
        experimento_id = experimento_id
        p_experimento = request.form['permissao_experimento']
        p_etapas = request.form['permissao_etapas']
        p_dispositivos = request.form['permissao_dispositivos']
        data_fim = request.form['data_fim']

        exp_arquivos = 'experimento_arquivos' in request.form
        exp_urls = 'experimento_urls' in request.form
        exp_anexos = [exp_arquivos, exp_urls]


        etp_arquivos = 'etapas_arquivos' in request.form
        etp_urls = 'etapas_urls' in request.form
        etp_anexos = [etp_arquivos, etp_urls]

        if data_fim:
            data_fim = date.fromisoformat(data_fim)
            
            cur.execute("""
                UPDATE local.permissoes 
                SET p_experimento = %s, p_etapas = %s, p_dispositivos = %s, fim = %s, exp_anexos = %s, etp_anexos = %s
                WHERE usuario_id = %s AND experimento_id = %s
                """, (p_experimento, p_etapas, p_dispositivos, data_fim, exp_anexos, etp_anexos, usuario_id, experimento_id))
            conn.commit()

            
        else:
            cur.execute("""
                UPDATE local.permissoes 
                SET p_experimento = %s, p_etapas = %s, p_dispositivos = %s, fim = NULL, exp_anexos = %s, etp_anexos = %s
                WHERE usuario_id = %s AND experimento_id = %s
                """, (p_experimento, p_etapas, p_dispositivos, exp_anexos, etp_anexos, usuario_id, experimento_id))
            conn.commit()

        return redirect(url_for('compartilhamento_experimento', user=current_user, experimento_id = experimento_id))
    else:
        return render_template('experimento-permissao.html', experimento_id = experimento_id, usuario_id=usuario_id,user=current_user, permissao=permissao, experimento=experimento, colaborador=colaborador, data_atual=data_atual)
        
@app.route('/detalhes-experimento/<int:experimento_id>/remover-permissao/<int:usuario_id>', methods=['GET'])
@login_required
@email_verificado_required
def remover_permissoes(experimento_id, usuario_id):
    cur = conn.cursor()
    cur.execute("""UPDATE api.experimento
        SET disponivel_para = array_remove(disponivel_para, %s)
        WHERE id = %s;
        """, (usuario_id, experimento_id))
    conn.commit()
    
    cur.execute("""UPDATE local.usuario
        SET acessos = array_remove(acessos, %s)
        WHERE id = %s;
        """, (experimento_id, usuario_id))
    conn.commit()
    
    cur.execute("""UPDATE local.solicitacoes 
        SET status = 'removida'
        WHERE status = 'aceita' AND solicitante_id = %s AND experimento_id = %s;
    """, (usuario_id, experimento_id))
    conn.commit()
    
    cur.execute("""DELETE FROM local.permissoes
        WHERE experimento_id = %s AND usuario_id = %s;
        """, (experimento_id, usuario_id))
    conn.commit()
    return redirect(url_for('compartilhamento_experimento', user=current_user, experimento_id = experimento_id))

@app.route('/formulario_requisicao/<int:id>', methods=['GET', 'POST'])
@login_required
def formulario_requisicao(id):
    if request.method == 'POST':
        nome_completo = request.form['nome']
        vinculo = request.form['vinculo']
        if vinculo == 'outro':
            vinculo = request.form['outro_vinculo']
        projeto = request.form['projeto']
        if projeto == 'outro':
            projeto = request.form['outro_projeto']
        orientador = request.form['orientador']
        tipos_dados_1 = 'tipo_dado_1' in request.form #Arquivos
        tipos_dados_2 = 'tipo_dado_2' in request.form #Links
        tipos_dados_3 = 'tipo_dado_3' in request.form #Sensores
        info_adicionais = request.form['info_adicionais']
        compromisso1 = 'compromisso1' in request.form
        compromisso2 = 'compromisso2' in request.form
        compromisso3 = 'compromisso3' in request.form
        compromisso4 = 'compromisso4' in request.form
        compromisso5 = 'compromisso5' in request.form
        compromisso6 = 'compromisso6' in request.form
        
        intencao = request.form['intencao']
        info_adicionais_req = request.form['info_adicionais_req']
        
        tipo_dados = [tipos_dados_1, tipos_dados_2, tipos_dados_3]
        
        solicitante_id = current_user.id
        experimento_id = id
        
        print(tipo_dados)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO local.solicitacoes 
                (solicitante_id, experimento_id,nome_completo, vinculo, projeto, orientador, tipo_dados, info_adicionais, intencao, info_adicionais_req, compromisso1, compromisso2, compromisso3, compromisso4, compromisso5, compromisso6) 
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s)
        """, (solicitante_id, experimento_id, nome_completo, vinculo, projeto, orientador, tipo_dados, info_adicionais, intencao, info_adicionais_req, compromisso1, compromisso2, compromisso3, compromisso4, compromisso5, compromisso6))
        
        conn.commit()
        
        
        
        return redirect(url_for('index', user=current_user))
    else:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM local.solicitacoes 
            WHERE status = 'aguardando' AND experimento_id = %s AND solicitante_id = %s
        """, (id, current_user.id))
        resp = cur.fetchone()
        if resp:
            aguardando = True
        else:
            aguardando = False
        return render_template('formulario.html', experimento_id=id, user=current_user, aguardando=aguardando)

    
#------------------------------------------------------------EXPERIMENTOS---------------------------------------------------------------------
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
    
@app.route('/inserir-experimento', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def inserir_experimento():
    if request.method == 'GET':
        return render_template('experimento-inserir.html', user=current_user)
    elif request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        categoria = request.form['categoria']
        outra_categoria = request.form['outra_categoria']
        if outra_categoria:
            categoria = outra_categoria
        localizacao = request.form['localizacao']

        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO api.experimento (titulo, descricao, categoria, localizacao, cadastrado_por) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (titulo, descricao, categoria, localizacao, current_user.id)
            )
            experimento_id = cur.fetchone()[0]
            conn.commit()
        except Exception as e:
            print('Erro ao criar experimento: ' + str(e), 'error')
            return redirect(url_for('inserir_experimento', user=current_user))

        if experimento_id:
            uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id))
            if not os.path.exists(uploads_dir):
                try:
                    os.makedirs(uploads_dir)
                except OSError as e:
                    print('Erro ao criar pasta de uploads: ' + str(e), 'error')
                    return redirect(url_for('inserir_experimento', user=current_user))
            return redirect(url_for('meus_experimentos', user=current_user))
        else:
            print('Erro ao recuperar o ID do experimento', 'error')
            return redirect(url_for('inserir_experimento', user=current_user))

            

    
@app.route('/detalhes-experimento/<int:experimento_id>/editar', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def editar_experimento(experimento_id):
    if request.method == 'GET':
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        print(experimento)
        return render_template('experimento-editar.html', experimento=experimento, experimento_id=experimento_id, user=current_user)
    elif request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        categoria = request.form['categoria']
        outra_categoria = request.form['outra_categoria']
        if outra_categoria:
            categoria = outra_categoria
        localizacao = request.form['localizacao']
        cur = conn.cursor()
        cur.execute("UPDATE api.experimento SET titulo=%s, descricao=%s, categoria=%s, localizacao=%s WHERE id=%s", (titulo, descricao, categoria, localizacao,experimento_id))
        conn.commit()
        return redirect(url_for('detalhes_experimento', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/deletar', methods=['GET'])
@login_required
@email_verificado_required
def deletar_experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("""
        UPDATE local.usuario
        SET acessos = array_remove(acessos, %s);
    """, (experimento_id,))
    conn.commit()
    
    cur.execute("DELETE FROM api.experimento WHERE id = %s", (experimento_id,))
    conn.commit()

    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id))
    if os.path.exists(uploads_dir):
        try:
            shutil.rmtree(uploads_dir)
        except Exception as e:
            flash('Erro ao deletar a pasta de uploads: ' + str(e), 'error')
    return redirect(url_for('meus_experimentos', user=current_user))

    
@app.route('/experimento/<int:experimento_id>')
@login_required
@email_verificado_required
def experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('index-experimento.html', experimento = experimento, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>')
@login_required
@email_verificado_required
def detalhes_experimento(experimento_id):
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] ==  experimento_id:
            permissao_usuario = permissao
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) FROM api.anexos_experimento WHERE experimento_id = %s", (experimento_id,))
    count_anexos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM api.urls_experimento WHERE experimento_id = %s", (experimento_id,))
    count_urls = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM api.dispositivo WHERE experimento_id = %s", (experimento_id,))
    count_dispositivos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM api.etapa WHERE experimento_id = %s", (experimento_id,))
    count_etapas = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM local.solicitacoes WHERE experimento_id = %s AND status='aceita'", (experimento_id,))
    count_compartilhamentos = cur.fetchone()[0]
    
    counts = {
        "anexos": count_anexos,
        "urls": count_urls,
        "dispositivos": count_dispositivos,
        "etapas": count_etapas,
        "compartilhamentos": count_compartilhamentos
    }
    
    folder_path = f"./app/static/uploads/{experimento_id}/"
    folder_size = get_folder_size(folder_path)
    espaco_disco = folder_size / (1024 * 1024)
    espaco_disco = f"{espaco_disco:.2f} MB"
    
    
    #-- Para obter tamanhos individuais das tabelas de coleta/dispositivos de um experimento
    # SELECT * FROM tamanho_tabelas_experimento(experimento_id);


    #-- Para obter o tamanho total de todas as tabelas de coleta/dispositivos de um experimento
    # SELECT tamanho_total_experimento(experimento_id);

    
    cur.execute("SELECT tamanho_total_experimento(%s);", (experimento_id,))
    espaco_banco = cur.fetchone()[0]
    
    print(experimento)
    return render_template('experimento-detalhes.html', experimento = experimento,espaco_banco=espaco_banco, espaco_disco=espaco_disco, permissao = permissao_usuario, counts=counts, user=current_user)

@app.route('/meus-experimentos')
@login_required
@email_verificado_required
def meus_experimentos():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM api.experimento WHERE cadastrado_por = %s", (current_user.id,))
    experimentos_criados = cur.fetchall()
    for exp in experimentos_criados:
        exp['criado_em'] = exp['criado_em'].strftime('%Y-%m-%d às %H:%M')
    
    cur.execute("SELECT * FROM api.experimento WHERE %s = ANY (disponivel_para)", (current_user.id,))
    experimentos_disponiveis = cur.fetchall()
    for exp in experimentos_disponiveis:
        exp['criado_em'] = exp['criado_em'].strftime('%Y-%m-%d às %H:%M')

    return render_template('meus-experimentos.html', experimentos_criados=experimentos_criados, experimentos_disponiveis=experimentos_disponiveis, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/anexos', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def experimento_anexos(experimento_id):
    if request.method == 'POST':
        if 'file' in request.files:
            arquivo = request.files['file']
            descricao = request.form['descricao']
            sensivel = 'sensivel' in request.form
            if arquivo and allowed_file(arquivo.filename):
                nome_arquivo = secure_filename(arquivo.filename)
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER']+"/"+str(experimento_id), nome_arquivo)
                arquivo.save(caminho_arquivo)
                
                cur = conn.cursor()
                cur.execute("INSERT INTO api.anexos_experimento (experimento_id, nome_do_arquivo, caminho_do_arquivo, descricao, sensivel) VALUES (%s, %s, %s, %s, %s)", (experimento_id, nome_arquivo, caminho_arquivo, descricao, sensivel))
                conn.commit()
                
                return redirect(url_for('experimento_anexos', experimento_id=experimento_id, user=current_user))
            
    else:
        permissao_usuario = 'nenhuma'
        for permissao in current_user.permissoes:
            if permissao[0] ==  experimento_id:
                permissao_usuario = permissao
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.anexos_experimento WHERE experimento_id = %s", (experimento_id,))
        anexos = cur.fetchall()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('experimento-anexos.html', experimento_id=experimento_id, permissao=permissao_usuario,experimento=experimento,anexos=anexos, user=current_user)




@app.route('/detalhes-experimento/<int:experimento_id>/anexos/<int:anexo_id>/visualizar')
@login_required
@email_verificado_required
def download_anexos_experimento(experimento_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT nome_do_arquivo FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    nome_do_arquivo = resultado[0] if resultado else None

    if nome_do_arquivo:
        directory = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id))
        caminho_completo_arquivo = os.path.join(directory, nome_do_arquivo)
        
        if os.path.exists(caminho_completo_arquivo):
            try:
                return send_file(f"static/uploads/{experimento_id}/{nome_do_arquivo}")
            except Exception as e:
                print(f"Erro ao enviar o arquivo: {str(e)}")
                abort(500)
        else:
            print(f'Arquivo não encontrado no caminho: {caminho_completo_arquivo}')
            abort(404)
    else:
        print('Arquivo não encontrado no banco de dados')
        abort(404)

@app.route('/detalhes-experimento/<int:experimento_id>/anexos/<int:anexo_id>/deletar')
@login_required
@email_verificado_required
def deletar_anexos_experimento(experimento_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT nome_do_arquivo FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    nome_do_arquivo = resultado[0] if resultado else None
    
    directory = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id))
    caminho_completo_arquivo = os.path.join(directory, nome_do_arquivo)

    if os.path.exists(caminho_completo_arquivo):
        try:
            os.remove(caminho_completo_arquivo)
            cur = conn.cursor()
            cur.execute("DELETE FROM api.anexos_experimento WHERE nome_do_arquivo = %s AND experimento_id = %s", (nome_do_arquivo, experimento_id))
            conn.commit()

            return redirect(url_for('experimento_anexos', experimento_id=experimento_id))
        except OSError as e:
            print(f"Erro ao remover arquivo {caminho_completo_arquivo}: {e}")
            return 'Erro ao deletar o arquivo', 500
    else:
        return 'Arquivo não encontrado', 404

@app.route('/detalhes-experimento/<int:experimento_id>/url', methods=['GET','POST'])
@login_required
@email_verificado_required
def experimento_url(experimento_id):
    if request.method == 'POST':    
        url = request.form['url']
        nome_url = request.form['nome']
        descricao = request.form['descricao_url']
        cur = conn.cursor()
        cur.execute("INSERT INTO api.urls_experimento (experimento_id, url, nome_url, descricao) VALUES (%s, %s, %s, %s)", (experimento_id, url, nome_url, descricao))
        conn.commit()
    
        return redirect(url_for('experimento_url', experimento_id=experimento_id, user=current_user))
    else:
        permissao_usuario = 'nenhuma'
        for permissao in current_user.permissoes:
            if permissao[0] ==  experimento_id:
                permissao_usuario = permissao
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.urls_experimento WHERE experimento_id = %s", (experimento_id,))
        urls = cur.fetchall()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('experimento-urls.html', experimento_id=experimento_id, permissao=permissao_usuario,experimento=experimento, urls=urls, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/url/<int:url_id>/deletar')
@login_required
@email_verificado_required
def deletar_url_experimento(experimento_id, url_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.urls_experimento WHERE id = %s", (url_id,))
    conn.commit()

    return redirect(url_for('experimento_url', experimento_id=experimento_id, user=current_user))



@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo', methods=['GET'])
@login_required
@email_verificado_required
def experimento_dispositivos(experimento_id):
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] == experimento_id:
            permissao_usuario = permissao
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dispositivo WHERE experimento_id = %s ORDER BY criado_em LIMIT %s OFFSET %s", (experimento_id, per_page, offset))
    dispositivos = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM api.dispositivo WHERE experimento_id = %s", (experimento_id,))
    total_dispositivos = cur.fetchone()[0]
    total_pages = (total_dispositivos + per_page - 1) // per_page

    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()

    return render_template('experimento-dispositivos.html', 
                           experimento_id=experimento_id,
                           permissao=permissao_usuario, 
                           experimento=experimento,
                           dispositivos=dispositivos, 
                           user=current_user,
                           total_pages=total_pages, 
                           current_page=page)


@app.route('/download-config/<int:dispositivo_id>', methods=['GET'])
@login_required
@email_verificado_required
def download_config(dispositivo_id):
    cur = conn.cursor()
    cur.execute("SELECT token FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    dispositivo = cur.fetchone()

    if dispositivo is None:
        return "Dispositivo não encontrado.", 404

    dispositivo_token = dispositivo[0]  # Token do dispositivo
    data_redundancy_topic = f"valores/{dispositivo_id}"

    # Criando o conteúdo do cabeçalho
    config_content = f"""\
#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>

#define LED_1 4
#define LED_2 5

//---- WiFi settings
const char* ssid = "";  // nome de sua rede
const char* password = ""; // senha de sua rede
//---- MQTT Broker settings
const char* mqtt_server = "80fe29ce8268427c9a4a9aeb6cabf603.s2.eu.hivemq.cloud"; // URL do broker
const char* mqtt_username = ""; // nome de usuário
const char* mqtt_password = ""; // senha
const int mqtt_port = 8883; // porta do broker

WiFiClientSecure espClient;
PubSubClient client(espClient);
unsigned long lastMsg = 0;

const char* data_topic = "valores";
const int dispositivo_id = {dispositivo_id}; // ID do dispositivo
const char* data_redundancy_topic = "{data_redundancy_topic}"; // Tópico de redundância
const char* disp_token = "{dispositivo_token}"; // Token do dispositivo

#define MSG_BUFFER_SIZE (50)
char msg[MSG_BUFFER_SIZE];

static const char *root_ca PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)EOF";
"""

    # Buffer em memória
    buffer = io.BytesIO()
    buffer.write(config_content.encode('utf-8'))
    buffer.seek(0)

    # arquiv como resposta
    response = make_response(send_file(buffer, as_attachment=True, download_name=f"config_dispositivo_{dispositivo_id}.ino", mimetype='text/plain'))
    response.headers["Content-Disposition"] = f"attachment; filename=config_dispositivo_{dispositivo_id}.ino"
    return response


@app.route('/ativar-dispositivo/<int:experimento_id>/<int:dispositivo_id>', methods=['GET'])
@login_required
@email_verificado_required
def ativar_dispositivo(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("UPDATE api.dispositivo SET ativo = True WHERE id = %s;", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))
    
@app.route('/desativar-dispositivo/<int:experimento_id>/<int:dispositivo_id>', methods=['GET'])
@login_required
@email_verificado_required
def desativar_dispositivo(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("UPDATE api.dispositivo SET ativo = False WHERE id = %s;", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))
    



@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/inserir', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def experimento_dispositivos_inserir(experimento_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        mac_address = request.form['mac_address']
        
        ativo = 'false'
        
        cur = conn.cursor()
        cur.execute("INSERT INTO api.dispositivo (experimento_id, nome, mac_address, descricao, cadastrado_por, ativo) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", (experimento_id, nome, mac_address, descricao, current_user.id, ativo))
        conn.commit()
        
        dispositivo_id = cur.fetchone()[0]
        
        cur.execute("UPDATE api.dispositivo SET tabela_dispositivo = 'api.dados_dispositivo_%s'", (dispositivo_id,))
        conn.commit()
        

        fields = ', '.join([f'a{i+1} TEXT' for i in range(20)])

        
        comando_cria_tabela = f"CREATE TABLE api.dados_dispositivo_{dispositivo_id} (id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT current_timestamp, {fields});"
        cur.execute(comando_cria_tabela)
        conn.commit()
        
        cur.execute("SELECT id FROM api.coleta WHERE dispositivo_id = %s", (dispositivo_id,))
        coleta_id = cur.fetchone()[0]
        
        cur.execute("UPDATE api.coleta SET tabela_coleta = 'api.dados_coleta_%s' WHERE id=%s", (coleta_id, coleta_id))  
        conn.commit()
        
        
        comando_cria_tabela = f"CREATE TABLE api.dados_coleta_{coleta_id} (id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT current_timestamp);"
        cur.execute(comando_cria_tabela)
        conn.commit()
        
        
        return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id))
            
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('dispositivo-inserir.html', experimento_id=experimento_id, experimento=experimento, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/editar', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def experimento_dispositivo_editar(experimento_id, dispositivo_id):
    if request.method == 'GET':
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
        dispositivo = cur.fetchone()
        
        return render_template('dispositivo-editar.html', dispositivo=dispositivo, experimento_id=experimento_id, dispositivo_id=dispositivo_id, user=current_user)

    elif request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        mac_address = request.form['mac_address']
        
        ativo = 'false'

        cur = conn.cursor()
        cur.execute("UPDATE api.dispositivo SET nome=%s, descricao=%s, mac_address=%s, ativo=%s WHERE id=%s", (nome, descricao, mac_address, ativo, dispositivo_id))
        conn.commit()
        return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/deletar')
@login_required
@email_verificado_required
def experimento_dispositivo_deletar(experimento_id, dispositivo_id):
    cur = conn.cursor()
    
    comando_deleta_tabela = f"DROP TABLE api.dados_dispositivo_{dispositivo_id};"
    cur.execute(comando_deleta_tabela)
    conn.commit()
    
    cur.execute("SELECT id FROM api.coleta WHERE dispositivo_id = %s", (dispositivo_id,))
    coletas = cur.fetchall()
    for coleta in coletas:
        comando_deleta_tabela_coleta = f"DROP TABLE api.dados_coleta_{coleta[0]};"
        print(comando_deleta_tabela_coleta)
        cur.execute(comando_deleta_tabela_coleta)
    
    cur.execute("DELETE FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/dados', methods=['GET'])
@login_required
@email_verificado_required
def dispositivo_dados(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    dispositivo = cur.fetchone()

    cur = conn.cursor()
    tabela = f"api.dados_dispositivo_{dispositivo_id}"
    cur.execute(f"SELECT * FROM {tabela};")
    dados = cur.fetchall()
        
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    
    
    return render_template('dispositivo-dados.html', experimento_id=experimento_id,dispositivo=dispositivo, dispositivo_id=dispositivo_id, dados=dados,experimento=experimento, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/dados/limpar')
@login_required
@email_verificado_required
def dispositivo_dados_limpar(experimento_id, dispositivo_id):
    cur = conn.cursor()
    
    comando_limpa_tabela = f"DELETE FROM api.dados_dispositivo_{dispositivo_id};"
    cur.execute(comando_limpa_tabela)
    conn.commit()

    return redirect(url_for('dispositivo_dados', experimento_id=experimento_id, dispositivo_id=dispositivo_id, user=current_user))


####################################################    COLETAS    #########################################################
############################################################################################################################

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/', methods=['GET'])
@login_required
@email_verificado_required
def experimento_dispositivo_coleta(experimento_id, dispositivo_id):
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] ==  experimento_id:
            permissao_usuario = permissao

    cur = conn.cursor()
    cur.execute("SELECT * FROM api.coleta WHERE dispositivo_id = %s ORDER BY nome", (dispositivo_id,))
    coletas = cur.fetchall()
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    dispositivo = cur.fetchone()
        
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    
    return render_template('dispositivo-coleta.html', experimento_id=experimento_id, dispositivo=dispositivo, permissao=permissao_usuario, dispositivo_id=dispositivo_id, coletas=coletas,experimento=experimento, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/inserir', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def coleta_inserir(experimento_id, dispositivo_id):
    if request.method == 'POST':
        nome = request.form['nome']
        atributos = request.form.getlist('coluna[]')

        atributos_detalhes = []
        for i in range(0, len(atributos), 4):
            atributo = {
                'nome': atributos[i],
                'descricao': atributos[i+1],
                'tipo': atributos[i+2],
                'unidade': atributos[i+3]
            }
            atributos_detalhes.append(atributo)
        atributos_json = json.dumps(atributos_detalhes)
        
        
        cur = conn.cursor()
        cur.execute("UPDATE api.coleta SET status = false, data_fechamento = current_timestamp WHERE dispositivo_id = %s", (dispositivo_id,))
        conn.commit()
        
        
        cur.execute("INSERT INTO api.coleta (dispositivo_id, nome, atributos) VALUES (%s, %s, %s) RETURNING id", (dispositivo_id, nome, [atributos_json]))
        conn.commit()
        
        coleta_id = cur.fetchone()[0]
        
        cur.execute("UPDATE api.coleta SET tabela_coleta = 'api.dados_coleta_%s' WHERE id=%s", (coleta_id, coleta_id))  
        conn.commit()
        
        if len(atributos_detalhes) > 0:
            fields = ', '.join([f'a{i+1} TEXT' for i in range((len(atributos_detalhes)))])
        else:
            fields = False
        
        if fields:
            comando_cria_tabela = f"CREATE TABLE api.dados_coleta_{coleta_id} (id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT current_timestamp, {fields});"
        else:
            comando_cria_tabela = f"CREATE TABLE api.dados_coleta_{coleta_id} (id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT current_timestamp);"
        print(comando_cria_tabela)
        
        cur.execute(comando_cria_tabela)
        conn.commit()
        
        return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id))
            
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
        dispositivo = cur.fetchone()
        return render_template('dispositivo-coleta-inserir.html', experimento_id=experimento_id, dispositivo=dispositivo,experimento=experimento, user=current_user)


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/<int:coleta_id>/editar', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def coleta_editar(experimento_id, dispositivo_id, coleta_id):
    if request.method == 'GET':
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.coleta WHERE id = %s", (coleta_id,))
        coleta = cur.fetchone()
        print(coleta)
        if coleta:
            coleta_json = {
                'id': coleta_id,
                'nome': coleta[1],
                'atributos': []
            }
            if coleta[3]:  # Verifica se o campo de colunas não está vazio
                string=coleta[3][0]
                lista = json.loads(string)  # Converte a string JSON em objeto Python
                for item in lista:
                    coleta_json['atributos'].append(item)

            return render_template('dispositivo-coleta-editar.html', coleta=coleta_json, experimento_id=experimento_id, coleta_id=coleta_id, dispositivo_id=dispositivo_id, user=current_user)
        else:
            # Lidar com o caso em que o dispositivo não foi encontrado no banco de dados
            return "Dispositivo não encontrado."

    elif request.method == 'POST':
        nome = request.form['nome']
        colunas = request.form.getlist('coluna[]')

        colunas_detalhes = []
        for i in range(0, len(colunas), 4):
            coluna = {
                'nome': colunas[i],
                'tipo': colunas[i+1],
                'unidade': colunas[i+2],
                'descricao': colunas[i+3]
            }
            colunas_detalhes.append(coluna)
        colunas_json = json.dumps(colunas_detalhes)
        ativo = 'false'

        print("UPDATE api.coleta SET nome=%s, atributos=%s WHERE id=%s", (nome, [colunas_json], coleta_id))
        cur = conn.cursor()
        cur.execute("UPDATE api.coleta SET nome=%s, atributos=%s WHERE id=%s", (nome, [colunas_json], coleta_id))
        conn.commit()
        return redirect(url_for('coleta_editar', experimento_id=experimento_id,dispositivo_id=dispositivo_id, coleta_id=coleta_id, user=current_user))


@app.route('/adicionar-coluna/<int:experimento_id>/<int:coleta_id>/<int:n_atributo>', methods=['POST'])
@login_required
@email_verificado_required
def adicionar_atributo(experimento_id, coleta_id, n_atributo):
    try:
        cur = conn.cursor()

        table_name = f'api.dados_coleta_{coleta_id}'
        coluna_name = f'a{n_atributo}'

        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {coluna_name} TEXT;")
        #print(f"ALTER TABLE {table_name} ADD COLUMN {coluna_name} TEXT;")
        conn.commit()

        return jsonify({'message': f'Coluna {coluna_name} adicionada com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
@app.route('/remove-coluna/<int:experimento_id>/<int:coleta_id>/<int:n_atributo>//<int:total_atributos>', methods=['POST'])
@login_required
@email_verificado_required
def remover_atributo(experimento_id, coleta_id, n_atributo, total_atributos):
    try:
        cur = conn.cursor()

        table_name = f'api.dados_coleta_{coleta_id}'
        coluna_name = f'a{n_atributo}'

        if n_atributo==total_atributos:
            cur.execute(f"ALTER TABLE {table_name} DROP COLUMN {coluna_name};")
        elif n_atributo<total_atributos:
            cur.execute(f"ALTER TABLE {table_name} DROP COLUMN {coluna_name};")
            i = n_atributo
            while i<total_atributos:
                 cur.execute(f"ALTER TABLE {table_name} RENAME COLUMN a{i+1} TO a{i};")
                 i=i+1
        
        conn.commit()

        return jsonify({'message': f'Coluna {coluna_name} removida com sucesso'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/<int:coleta_id>/dados', methods=['GET'])
@login_required
@email_verificado_required
def coleta_dados(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.coleta WHERE id = %s", (coleta_id,))
    coleta = cur.fetchone()
    if coleta:
        coleta_json = {
            'id': coleta_id,
            'nome': coleta[1],
            'status': coleta[4],
            'data_inicio': coleta[5],
            'data_fechamento': coleta[6],
            'tabela_dados': coleta[7],
            'atributos': []    
        }
        if coleta[3]:  
            string=coleta[3][0]
            lista = json.loads(string)  
            for item in lista:
                coleta_json['atributos'].append(item)

        cur = conn.cursor()
        tabela = coleta_json.get('tabela_dados').replace("'", "")
        print(tabela)
        cur.execute(f"SELECT * FROM {tabela};")
        dados = cur.fetchall()
        
        varia = 2
        for atributo in coleta_json["atributos"]:
            experimento_dispositivo_grafico(coleta_id, varia, atributo)
            varia = varia+1
            
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
        dispositivo = cur.fetchone()
        
        return render_template('dispositivo-coleta-dados.html', experimento_id=experimento_id,dispositivo=dispositivo, coleta=coleta_json, dispositivo_id=dispositivo_id, dados=dados,experimento=experimento, user=current_user)



@app.route('/abrir-coleta/<int:experimento_id>/<int:dispositivo_id>/<int:coleta_id>', methods=['GET'])
@login_required
@email_verificado_required
def abrir_coleta(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    
    cur.execute("UPDATE api.coleta SET status = False, data_fechamento = current_timestamp WHERE dispositivo_id = %s;", (dispositivo_id,))
    conn.commit()
    
    cur.execute("UPDATE api.coleta SET status = True, data_fechamento = null WHERE id = %s;", (coleta_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))

@app.route('/fechar-coleta/<int:experimento_id>/<int:dispositivo_id>/<int:coleta_id>', methods=['GET'])
@login_required
@email_verificado_required
def fechar_coleta(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    
    cur.execute("UPDATE api.coleta SET status = False, data_fechamento = current_timestamp WHERE id = %s;", (coleta_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/<int:coleta_id>/deletar')
@login_required
@email_verificado_required
def coleta_deletar(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    
    comando_deleta_tabela = f"DROP TABLE api.dados_coleta_{coleta_id};"
    
    cur.execute(comando_deleta_tabela)
    conn.commit()
    
    cur.execute("DELETE FROM api.coleta WHERE id = %s", (coleta_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/<int:coleta_id>/limpar')
@login_required
@email_verificado_required
def coleta_limpar(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    
    comando_limpar_tabela = f"DELETE FROM api.dados_coleta_{coleta_id};"
    cur.execute(comando_limpar_tabela)
    conn.commit()
    
    print(comando_limpar_tabela)

    return redirect(url_for('coleta_dados', experimento_id=experimento_id, dispositivo_id=dispositivo_id, coleta_id=coleta_id, user=current_user))

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/grafico/<int:coluna_id>/<coluna>')
def experimento_dispositivo_grafico(coleta_id, coluna_id, coluna):
    coluna_dict = coluna
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dados_coleta_%s", (coleta_id,))
    coletas = cur.fetchall()
    
    datas = [coleta[1] for coleta in coletas]
    #print(datas)
    tipo_coluna = coluna_dict.get('tipo')
    if tipo_coluna == 'REAL' or tipo_coluna == 'real':
        valores = []
        for coleta in coletas:
            try:
                valor = float(coleta[coluna_id])
            except ValueError:
                valor = None 
            valores.append(valor)
    else:
        valores = [coleta[coluna_id] for coleta in coletas]

    # Converter as datas para um formato adequado para plotagem
    datas_plot = [(datetime.strptime(str(data), '%Y-%m-%d %H:%M:%S.%f') - timedelta(hours=3)).strftime('%d/%m %H:%M') for data in datas]


    plt.figure(figsize=(18, 8))
    
    # Plotar o gráfico
    plt.plot(datas_plot, valores, marker='', linestyle='-')
    plt.xlabel('Data da Coleta')
    plt.ylabel('Valor da Coleta (' + coluna_dict['unidade'] + ')')
    plt.title('Gráfico da Coluna ' + coluna_dict['nome'] + ':\n' + coluna_dict['descricao'])
    plt.xticks(rotation=45)
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(nbins=25))

    
    #plt.text(0.5, 0.5, coluna_dict['descricao'], verticalalignment='bottom', horizontalalignment='center',  transform=plt.gca().transAxes, fontsize=10)
    
    plt.tight_layout()
    # Salvar o gráfico como uma imagem
    imagem_grafico = f'/home/allan/pibiti/plataforma_gestao_agropecuaria/app/static/graficos/grafico-{coleta_id}-{coluna_dict["nome"]}.png'
    
    plt.savefig(imagem_grafico)
    plt.close()
    
    # Enviar a imagem como resposta
    #return send_file(imagem_grafico, mimetype='image/png')
    return

#------------------------------------------------------------ETAPAS-------------------------------------------------------------------------
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

@app.route('/detalhes-experimento/<int:experimento_id>/etapas', methods=['GET'])
@login_required
@email_verificado_required
def etapas_experimento(experimento_id):
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] ==  experimento_id:
            permissao_usuario = permissao
    
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    
    cur.execute("SELECT * FROM api.etapa WHERE experimento_id = %s ORDER BY ordem", (experimento_id,))
    etapas = cur.fetchall()
    
    
    list_etapas = []
    for etapa in etapas:
        etapa_id = etapa[0]

        cur.execute("SELECT COUNT(*) FROM api.anexos_etapa WHERE etapa_id = %s", (etapa_id,))
        count_anexos_etapa = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM api.urls_etapa WHERE etapa_id = %s", (etapa_id,))
        count_urls_etapa = cur.fetchone()[0]
        
        etapa_list = list(etapa)
        etapa_list.append(count_anexos_etapa)
        etapa_list.append(count_urls_etapa)
        list_etapas.append(etapa_list)

    cur.execute("SELECT COUNT(*) FROM api.dispositivo WHERE experimento_id = %s", (experimento_id,))
    count_dispositivos = cur.fetchone()[0]
    
    return render_template('etapas-detalhes.html', experimento_id=experimento_id, experimento=experimento,etapas=list_etapas, count_dispositivos=count_dispositivos,permissao=permissao_usuario, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/inserir', methods=['GET','POST'])
@login_required
@email_verificado_required
def inserir_etapa(experimento_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        status = request.form['status']
        experimento_id = experimento_id
        
        cur = conn.cursor()
        cur.execute("INSERT INTO api.etapa (nome, descricao, status, experimento_id) VALUES (%s, %s, %s, %s) RETURNING id", (nome, descricao, status, experimento_id))
        etapa_id = cur.fetchone()[0]
        conn.commit()
        if etapa_id:
            uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id)+"/"+str(etapa_id))
            if not os.path.exists(uploads_dir):
                try:
                    os.makedirs(uploads_dir)
                except OSError as e:
                    print('Erro ao criar pasta de uploads: ' + str(e), 'error')
        return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))
    else:
        return render_template('etapa-inserir.html', experimento_id=experimento_id, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/ordem', methods=['GET'])
@login_required
@email_verificado_required
def ordem_etapa(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.etapa WHERE experimento_id = %s ORDER BY ordem;", (experimento_id,))
    etapas = cur.fetchall()
    return render_template('etapas-ordem.html', etapas=etapas, experimento_id=experimento_id,user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/atualizar_ordem', methods=['POST'])
@login_required
@email_verificado_required
def atualizar_ordem(experimento_id):
    data = request.get_json()
    nova_ordem = data.get('novaOrdem')
    
    cur = conn.cursor()
    
    for item in nova_ordem:
        idx = item.get('index')
        texto = item.get('texto')
        txt = texto.split()
        id = txt[-1]
        cur.execute("UPDATE api.etapa SET ordem = %s WHERE id = %s;", (idx, id))
    conn.commit()
    
    return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/anexos', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def etapa_anexos(experimento_id, etapa_id):
    if request.method == 'POST':
        if 'file' in request.files:
            arquivo = request.files['file']
            descricao = request.form['descricao']
            if arquivo and allowed_file(arquivo.filename):
                nome_arquivo = secure_filename(arquivo.filename)
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER']+"/"+str(experimento_id)+"/"+str(etapa_id), nome_arquivo)
                arquivo.save(caminho_arquivo)
                
                cur = conn.cursor()
                cur.execute("INSERT INTO api.anexos_etapa (etapa_id, nome_do_arquivo, caminho_do_arquivo, descricao) VALUES (%s, %s, %s, %s)", (etapa_id, nome_arquivo, caminho_arquivo, descricao))
                conn.commit()
                
                return redirect(url_for('etapa_anexos', experimento_id=experimento_id, etapa_id=etapa_id, user=current_user))
            
    else:
        permissao_usuario = 'nenhuma'
        for permissao in current_user.permissoes:
            if permissao[0] ==  experimento_id:
                permissao_usuario = permissao
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.anexos_etapa WHERE etapa_id = %s", (etapa_id,))
        anexos = cur.fetchall()
        cur.execute("SELECT * FROM api.etapa WHERE id = %s", (etapa_id,))
        etapa = cur.fetchone()
        
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('etapa-anexos.html', experimento_id=experimento_id, permissao=permissao_usuario, etapa_id=etapa_id, experimento=experimento,etapa=etapa,anexos=anexos, user=current_user)
            
@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/editar', methods=['GET', 'POST'])
@login_required
@email_verificado_required
def editar_etapa(experimento_id, etapa_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        status = request.form['status']
        experimento_id = experimento_id
        
        cur = conn.cursor()
        cur.execute("UPDATE api.etapa SET nome = %s, descricao = %s, status = %s WHERE id = %s", (nome, descricao, status, etapa_id,))
        conn.commit()
        flash('Etapa editada com sucesso!', 'success')
        return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.etapa WHERE id = %s", (etapa_id,))
        etapas = cur.fetchall()
        print(etapas[0])
        return render_template('etapa-editar.html', experimento_id=experimento_id,etapa=etapas[0], user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/deletar', methods=['GET'])
@login_required
@email_verificado_required
def deletar_etapa(experimento_id, etapa_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.etapa WHERE id = %s", (etapa_id,))
    
    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id)+"/"+str(etapa_id))
    if os.path.exists(uploads_dir):
        try:
            shutil.rmtree(uploads_dir)
        except Exception as e:
            flash('Erro ao deletar a pasta de uploads: ' + str(e), 'error')
    return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/anexos/<int:anexo_id>/visualizar')
@login_required
@email_verificado_required
def download_anexo(experimento_id, etapa_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT nome_do_arquivo FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    nome_do_arquivo = resultado[0] if resultado else None

    if nome_do_arquivo:
        directory = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id)+"/"+str(etapa_id))
        caminho_completo_arquivo = os.path.join(directory, nome_do_arquivo)
        
        if os.path.exists(caminho_completo_arquivo):
            try:
                return send_file(f"static/uploads/{experimento_id}/{etapa_id}/{nome_do_arquivo}")
            except Exception as e:
                print(f"Erro ao enviar o arquivo: {str(e)}")
                abort(500)
        else:
            print(f'Arquivo não encontrado no caminho: {caminho_completo_arquivo}')
            abort(404)
    else:
        print('Arquivo não encontrado no banco de dados')
        abort(404)


@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/anexos/<int:anexo_id>/deletar')
@login_required
@email_verificado_required
def deletar_anexos_etapa(experimento_id,etapa_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT nome_do_arquivo FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    nome_do_arquivo = resultado[0] if resultado else None
    
    directory = os.path.join(app.config['UPLOAD_FOLDER'], str(experimento_id)+"/"+str(etapa_id))
    caminho_completo_arquivo = os.path.join(directory, nome_do_arquivo)

    if os.path.exists(caminho_completo_arquivo):
        try:
            os.remove(caminho_completo_arquivo)
            cur = conn.cursor()
            cur.execute("DELETE FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
            conn.commit()
    
            return redirect(url_for('experimento_anexos', experimento_id=experimento_id))
        except OSError as e:
            print(f"Erro ao remover arquivo {caminho_completo_arquivo}: {e}")
            return 'Erro ao deletar o arquivo', 500
    else:
        return 'Arquivo não encontrado', 404


@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/url', methods=['GET','POST'])
@login_required
@email_verificado_required
def etapa_url(experimento_id, etapa_id):
    if request.method == 'POST':
        url = request.form['url']
        nome_url = request.form['nome']
        descricao = request.form['descricao_url']
        cur = conn.cursor()
        cur.execute("INSERT INTO api.urls_etapa (etapa_id, url, nome_url, descricao) VALUES (%s, %s, %s, %s)", (etapa_id, url, nome_url, descricao))
        conn.commit()
        
        return redirect(url_for('etapa_url', experimento_id=experimento_id, etapa_id=etapa_id, user=current_user))
    else:
        permissao_usuario = 'nenhuma'
        for permissao in current_user.permissoes:
            if permissao[0] ==  experimento_id:
                permissao_usuario = permissao
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.urls_etapa WHERE etapa_id = %s", (etapa_id,))
        urls = cur.fetchall()
        print(urls)
        cur.execute("SELECT * FROM api.etapa WHERE id = %s", (etapa_id,))
        etapa = cur.fetchone()
        
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('etapa-urls.html', experimento_id=experimento_id, permissao=permissao_usuario,etapa_id=etapa_id, experimento=experimento,etapa=etapa, urls=urls, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/url/<int:url_id>/deletar')
@login_required
@email_verificado_required
def deletar_url_etapa(experimento_id,etapa_id, url_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.urls_etapa WHERE id = %s", (url_id,))
    conn.commit()

    return redirect(url_for('etapa_url', etapa_id=etapa_id, experimento_id=experimento_id, user=current_user))


###################################################################################################################################################
#######################################################  ADMIN  ###################################################################################

@app.route('/admin/usuarios', methods=['GET', 'POST'])
@login_required 
@email_verificado_required
@admin_required
def admin_usuarios():
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            senha = request.form.get('senha')

            cur = conn.cursor()
            cur.execute("SELECT id FROM local.usuario WHERE email = %s", (email,))
            existing_user = cur.fetchone()

            if existing_user:
                flash('Este email já está registrado.', 'danger')
                return redirect(url_for('admin_usuarios'))
            user = auth.create_user(
                email=email,
                password=senha
            )

            cur.execute("INSERT INTO local.usuario (nome, email, senha, vinculo) VALUES (%s, %s, %s, %s)",
                        ('Novo Usuário', email, senha, 'Desconhecido'))
            conn.commit()

            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin_usuarios'))
        firebase_users = []
        page = auth.list_users()
        while page:
            for user in page.users:
                firebase_users.append({
                    'uid': user.uid,
                    'email': user.email if hasattr(user, 'email') else None,
                    'email_verified': user.email_verified if hasattr(user, 'email_verified') else False
                })
            page = page.get_next_page()

        cur = conn.cursor()
        cur.execute("SELECT id, email, nome, vinculo, admin FROM local.usuario")
        postgres_users = cur.fetchall()

        user_data = []
        for postgres_user in postgres_users:
            for firebase_user in firebase_users:
                if postgres_user[1] == firebase_user['email']:
                    user_data.append({
                        'id': postgres_user[0],
                        'email': postgres_user[1],
                        'nome': postgres_user[2],
                        'vinculo': postgres_user[3],
                        'admin': postgres_user[4],
                        'firebase_uid': firebase_user['uid'],
                        'email_verified': firebase_user['email_verified']
                    })

        return render_template('admin_usuarios.html', user=current_user, users=user_data)

    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        flash("Erro ao listar usuários. Tente novamente mais tarde.", "danger")
        return "Erro ao carregar usuários", 500



# Excluir Usuário
@app.route('/admin/excluir/<uid>/<db_id>', methods=['GET'])
@login_required
@email_verificado_required
@admin_required
def excluir_usuario(uid, db_id):
    try:
        auth.delete_user(uid)

        cur = conn.cursor()
        cur.execute("DELETE FROM local.usuario WHERE id = %s", (db_id,))
        conn.commit()
        
        flash("Usuário excluído com sucesso.", "success")
        return redirect(url_for('admin_usuarios'))

    except Exception as e:
        print(f"Erro ao excluir usuário: {e}")
        flash("Erro ao excluir usuário. Tente novamente.", "danger")
        return redirect(url_for('admin_usuarios'))



@app.route('/admin/tornar-admin/<db_id>', methods=['GET'])
@login_required
@email_verificado_required
@admin_required
def toggle_admin(db_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT admin FROM local.usuario WHERE id = %s", (db_id,))
        is_admin = cur.fetchone()[0] 

        new_status = not is_admin
        cur.execute("UPDATE local.usuario SET admin = %s WHERE id = %s", (new_status, db_id))
        conn.commit()

        if new_status:
            flash("Usuário promovido a admin com sucesso.", "success")
        else:
            flash("Privilégios de admin removidos com sucesso.", "success")

        return redirect(url_for('admin_usuarios'))

    except Exception as e:
        print(f"Erro ao alternar status de admin: {e}")
        flash("Erro ao alterar o status de admin. Tente novamente.", "danger")
        return redirect(url_for('admin_usuarios'))


# Rota para exibir e gerenciar os domínios permitidos
@app.route('/admin/dominios', methods=['GET', 'POST'])
@login_required
@email_verificado_required
@admin_required
def admin_dominios():
    cur = conn.cursor()

    if request.method == 'POST':
        novo_dominio = request.form['dominio']
        try:
            cur.execute("INSERT INTO local.dominios (dominio) VALUES (%s)", (novo_dominio,))
            conn.commit()
            print(f"Domínio {novo_dominio} adicionado com sucesso.")
        except Exception as e:
            print(f"Erro ao adicionar o domínio: {e}")

    
    cur.execute("SELECT * FROM local.dominios")
    dominios = cur.fetchall()

    return render_template('admin-dominios.html', user=current_user, dominios=dominios)

# Rota para remover um domínio
@app.route('/admin/dominios/remover/<int:id>', methods=['POST'])
@login_required
@email_verificado_required
@admin_required
def remover_dominio(id):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM local.dominios WHERE id = %s", (id,))
        conn.commit()
        print("Domínio removido com sucesso.")
    except Exception as e:
        print(f"Erro ao remover o domínio: {e}")

    return redirect(url_for('admin_dominios'))



if __name__ == "__main__":
    #app.run(host='0.0.0.0', port=5002,threaded=True)
    app.run(debug=True, threaded=True, port=5003)

