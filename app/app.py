from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
import psycopg2 #pip install psycopg2 
import psycopg2.extras
from werkzeug.utils import secure_filename
import os
import json
import matplotlib
import matplotlib.ticker as ticker
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
from threading import Thread
import pandas as pd

from jinja2 import Template

# Configurações postgresql

#DB_HOST = "localhost"
DB_HOST = "10.0.2.15"
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

app.config['UPLOAD_FOLDER'] = 'app/static/uploads'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, nome, senha, nome_completo, vinculo, acessos, permissoes):
        self.id = id
        self.nome = nome
        self.senha = senha
        self.nome_completo = nome_completo
        self.vinculo = vinculo
        self.acessos = acessos
        self.permissoes = permissoes
        
@login_manager.user_loader
def load_user(user_id):
    cur = conn.cursor()
    cur.execute("SELECT id, nome, senha, nome_completo, vinculo, acessos FROM local.usuario WHERE id = %s", (user_id,))
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
        user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5], permissions_data)
        
        
        return user
    else:
        return None


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



@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'GET':
        user_id = current_user.id
        nome = current_user.nome
        senha = current_user.senha
        nome_completo = current_user.nome_completo
        vinculo = current_user.vinculo
        return render_template('perfil.html', user_id=user_id, nome=nome, senha=senha, nome_completo=nome_completo, vinculo=vinculo, user=current_user)
    elif request.method == 'POST':
        print('a')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user() 
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('index', user=current_user))

@app.route('/login',  methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', user=current_user)
    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        cur = conn.cursor()
        cur.execute("SELECT id FROM local.usuario WHERE nome = %s and senha = %s", (nome, senha))        
        user_id = cur.fetchone() 
        if user_id:
            user = load_user(user_id)
            login_user(user)  
            flash('Login bem sucedido!', 'success')
            return redirect(url_for('perfil', user=current_user))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
            return redirect(url_for('login', user=current_user))


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('cadastro.html', user=current_user)
    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        nome_completo = request.form['nome_completo']
        vinculo = request.form['vinculo']
        cur = conn.cursor()
        cur.execute("INSERT INTO local.usuario (nome, senha, nome_completo, vinculo) VALUES (%s, %s, %s, %s)", (nome, senha, nome_completo, vinculo))
        conn.commit()
        print("Registro POST recebido")
        print("Nome de usuário:", nome)
        print("Senha:", senha)
        flash('Registro bem sucedido! Faça login para continuar.', 'success')

        return redirect(url_for('login', user=current_user))
    
@app.route('/editar-perfil', methods=['GET', 'POST'])
def editar_perfil():
    if request.method == 'GET':
        nome = current_user.nome
        senha = current_user.senha
        nome_completo = current_user.nome_completo
        vinculo = current_user.vinculo
        return render_template('perfil-editar.html', nome=nome, senha=senha, nome_completo=nome_completo, vinculo=vinculo, user=current_user)
    elif request.method == 'POST':
        nome = request.form['username']
        senha = request.form['password']
        nome_completo = request.form['nome_completo']
        vinculo = request.form['vinculo']
        cur = conn.cursor()
        cur.execute("UPDATE local.usuario SET nome=%s, senha=%s, nome_completo=%s, vinculo=%s WHERE id=%s", (nome, senha, nome_completo, vinculo, current_user.id))
        conn.commit()
        return redirect(url_for('perfil', user=current_user))
    
@app.route('/deletar-perfil', methods=['GET'])
def deletar_perfil():
    cur = conn.cursor()
    
    cur.execute("""UPDATE api.experimento
        SET disponivel_para = array_remove(disponivel_para, %s);
        """, (current_user.id,))
    conn.commit()
    
    cur.execute("DELETE FROM local.usuario WHERE id=%s", (current_user.id,))
    conn.commit()
    
    return redirect(url_for('logout', user=current_user))




#-------------------------------------------COMPARTILHAMENTO/FORMULARIO---------------------------------------------------------------------
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

@app.route('/compartilhados_experimento/<int:experimento_id>')
@login_required
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
    
    return render_template('experimento-compartilhado.html', usuarios=usuarios, experimento_id=experimento_id, experimento=experimento,user=current_user)



@app.route('/solicitacoes_experimento/<int:experimento_id>')
@login_required
def solicitacoes_experimento(experimento_id):
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM local.solicitacoes WHERE experimento_id = %s AND status= 'aguardando' ORDER BY data_hora DESC;", (experimento_id,))
    solicitacoes = cur.fetchall()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('experimento-solicitacoes.html', solicitacoes=solicitacoes, experimento_id = experimento_id, experimento=experimento, user=current_user)


@app.route('/historico-solicitacoes-experimento/<int:experimento_id>/<int:usuario_id>/')
@login_required
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
def recusar_solicitacao(experimento_id, solicitacao_id):
    cur = conn.cursor()
    cur.execute("UPDATE local.solicitacoes SET status='recusada' WHERE id = %s", (solicitacao_id,))
    conn.commit()
    return redirect(url_for('solicitacoes_experimento',  user=current_user, experimento_id=experimento_id))

@app.route('/aceitar-solicitacao/<int:id>')
@login_required
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
        cur = conn.cursor()
        cur.execute("INSERT INTO api.experimento (titulo, descricao, categoria, localizacao, cadastrado_por) VALUES (%s, %s, %s, %s, %s)", (titulo, descricao, categoria, localizacao, current_user.id))
        conn.commit()
        print("Registro POST recebido")
        print("titulo:", titulo)
        print("categoria:", categoria)
        flash('Registro bem sucedido! Faça login para continuar.', 'success')
        return redirect(url_for('meus_experimentos', user=current_user))
    
@app.route('/detalhes-experimento/<int:experimento_id>/editar', methods=['GET', 'POST'])
@login_required
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
def deletar_experimento(experimento_id):
    cur = conn.cursor()
    
    cur.execute("""UPDATE local.usuario
    SET acessos = array_remove(acessos, %s);
    """, (experimento_id,))
    conn.commit()
    
    
    cur.execute("DELETE FROM api.experimento WHERE id = %s", (experimento_id,))
    conn.commit()
    
    cur.execute("""    UPDATE local.usuario
        SET acessos = array_remove(acessos, %s);
        """, (experimento_id,))
    conn.commit()

    
    return redirect(url_for('meus_experimentos', user=current_user))
    
@app.route('/experimento/<int:experimento_id>')
@login_required
def experimento(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('index-experimento.html', experimento = experimento, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>')
@login_required
def detalhes_experimento(experimento_id):
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] ==  experimento_id:
            permissao_usuario = permissao
    
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    print(experimento)
    return render_template('experimento-detalhes.html', experimento = experimento, permissao = permissao_usuario ,user=current_user)

@app.route('/meus-experimentos')
@login_required
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
def experimento_anexos(experimento_id):
    if request.method == 'POST':
        if 'file' in request.files:
            arquivo = request.files['file']
            descricao = request.form['descricao']
            if arquivo and allowed_file(arquivo.filename):
                nome_arquivo = secure_filename(arquivo.filename)
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
                arquivo.save(caminho_arquivo)
                
                cur = conn.cursor()
                cur.execute("INSERT INTO api.anexos_experimento (experimento_id, nome_do_arquivo, caminho_do_arquivo, descricao) VALUES (%s, %s, %s, %s)", (experimento_id, nome_arquivo, caminho_arquivo, descricao))
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


@app.route('/detalhes-experimento/<int:experimento_id>/anexos/<int:anexo_id>/download')
@login_required
def download_anexos_experimento(experimento_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    caminho_do_arquivo = resultado[0] if resultado else None

    if caminho_do_arquivo:
        return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(caminho_do_arquivo)    )
    else:
        return 'Arquivo não encontrado', 404

@app.route('/detalhes-experimento/<int:experimento_id>/anexos/<int:anexo_id>/deletar')
@login_required
def deletar_anexos_experimento(experimento_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()

    cur.execute("DELETE FROM api.anexos_experimento WHERE id = %s", (anexo_id,))
    conn.commit()
    
    if resultado:
        caminho_do_arquivo = resultado[0]
        if os.path.exists(caminho_do_arquivo):
            os.remove(caminho_do_arquivo)


        return redirect(url_for('experimento_anexos', experimento_id=experimento_id, user=current_user))
    else:
        return 'Arquivo não encontrado', 404

@app.route('/detalhes-experimento/<int:experimento_id>/url', methods=['GET','POST'])
@login_required
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
def deletar_url_experimento(experimento_id, url_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.urls_experimento WHERE id = %s", (url_id,))
    conn.commit()

    return redirect(url_for('experimento_url', experimento_id=experimento_id, user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo', methods=['GET'])
@login_required
def experimento_dispositivos(experimento_id):
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] ==  experimento_id:
            permissao_usuario = permissao
    
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.dispositivo WHERE experimento_id = %s ORDER BY criado_em", (experimento_id,))
    dispositivos = cur.fetchall()
    print(dispositivos)
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('experimento-dispositivos.html', experimento_id=experimento_id,permissao=permissao_usuario, experimento=experimento,dispositivos=dispositivos, user=current_user)

@app.route('/ativar-dispositivo/<int:experimento_id>/<int:dispositivo_id>', methods=['GET'])
@login_required
def ativar_dispositivo(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("UPDATE api.dispositivo SET ativo = True WHERE id = %s;", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))
    
@app.route('/desativar-dispositivo/<int:experimento_id>/<int:dispositivo_id>', methods=['GET'])
@login_required
def desativar_dispositivo(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("UPDATE api.dispositivo SET ativo = False WHERE id = %s;", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))
    



@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/inserir', methods=['GET', 'POST'])
@login_required
def experimento_dispositivos_inserir(experimento_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        mac_address = request.form['mac_address']
        
        ativo = 'false'
        
        cur = conn.cursor()
        cur.execute("INSERT INTO api.dispositivo (experimento_id, nome, mac_address, descricao, cadastrado_por, ativo) VALUES (%s, %s, %s, %s, %s, %s)", (experimento_id, nome, mac_address, descricao, current_user.id, ativo))
        conn.commit()
        
        return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id))
            
    else:
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        return render_template('dispositivo-inserir.html', experimento_id=experimento_id, experimento=experimento, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/editar', methods=['GET', 'POST'])
@login_required
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

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/', methods=['GET'])
@login_required
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


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/deletar')
@login_required
def experimento_dispositivo_deletar(experimento_id, dispositivo_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id, user=current_user))

####################################################    COLETAS    #########################################################
############################################################################################################################


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/inserir', methods=['GET', 'POST'])
@login_required
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
        
        
        cur.execute("INSERT INTO api.coleta (dispositivo_id, nome, atributos) VALUES (%s, %s, %s)", (dispositivo_id, nome, [atributos_json]))
        conn.commit()
        
        return redirect(url_for('experimento_dispositivos', experimento_id=experimento_id))
            
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

            return render_template('dispositivo-coleta-editar.html', coleta=coleta_json, experimento_id=experimento_id, dispositivo_id=dispositivo_id, user=current_user)
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
                'descricao': colunas[i+1],
                'tipo': colunas[i+2],
                'unidade': colunas[i+3]
            }
            colunas_detalhes.append(coluna)
        colunas_json = json.dumps(colunas_detalhes)
        ativo = 'false'

        
        cur = conn.cursor()
        cur.execute("UPDATE api.coleta SET nome=%s, atributos=%s WHERE id=%s", (nome, [colunas_json], coleta_id))
        conn.commit()
        return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id,dispositivo_id=dispositivo_id, user=current_user))



@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/<int:coleta_id>/dados', methods=['GET'])
@login_required
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
            'atributos': []
        }
        if coleta[3]:  
            string=coleta[3][0]
            lista = json.loads(string)  
            for item in lista:
                coleta_json['atributos'].append(item)

        cur = conn.cursor()
        cur.execute("SELECT * FROM api.dados_coletados WHERE coleta_id = %s", (coleta_id,))
        dados = cur.fetchall()
        
        #varia = 1
        #for atributo in coleta_json["atributos"]:
        #    experimento_dispositivo_grafico(dispositivo_id, varia, atributo)
        #    varia = varia+1
            
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
        experimento = cur.fetchone()
        
        cur = conn.cursor()
        cur.execute("SELECT * FROM api.dispositivo WHERE id = %s", (dispositivo_id,))
        dispositivo = cur.fetchone()
        
        return render_template('dispositivo-coleta-dados.html', experimento_id=experimento_id,dispositivo=dispositivo, coleta=coleta_json, dispositivo_id=dispositivo_id, dados=dados,experimento=experimento, user=current_user)

@app.route('/abrir-coleta/<int:experimento_id>/<int:dispositivo_id>/<int:coleta_id>', methods=['GET'])
@login_required
def abrir_coleta(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    
    cur.execute("UPDATE api.coleta SET status = False, data_fechamento = current_timestamp WHERE dispositivo_id = %s;", (dispositivo_id,))
    conn.commit()
    
    cur.execute("UPDATE api.coleta SET status = True, data_fechamento = null WHERE id = %s;", (coleta_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))

@app.route('/fechar-coleta/<int:experimento_id>/<int:dispositivo_id>/<int:coleta_id>', methods=['GET'])
@login_required
def fechar_coleta(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    
    cur.execute("UPDATE api.coleta SET status = False, data_fechamento = current_timestamp WHERE id = %s;", (coleta_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))

@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/<int:coleta_id>/deletar')
@login_required
def coleta_deletar(experimento_id, dispositivo_id, coleta_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.coleta WHERE id = %s", (coleta_id,))
    conn.commit()

    return redirect(url_for('experimento_dispositivo_coleta', experimento_id=experimento_id, dispositivo_id=dispositivo_id,user=current_user))


@app.route('/detalhes-experimento/<int:experimento_id>/dispositivo/<int:dispositivo_id>/coleta/grafico/<int:coluna_id>/<coluna>')
def experimento_dispositivo_grafico(dispositivo_id, coluna_id, coluna):
    coluna_dict = coluna
    cur = conn.cursor()
    cur.execute("SELECT a%s, gerado_em  FROM api.coleta WHERE dispositivo_id = %s", (coluna_id, dispositivo_id,))
    coletas = cur.fetchall()
    
    datas = [coleta[1] for coleta in coletas]
    print(datas)
    tipo_coluna = coluna_dict.get('tipo')
    if tipo_coluna == 'REAL' or tipo_coluna == 'real':
        valores = []
        for coleta in coletas:
            try:
                valor = float(coleta[0])
            except ValueError:
                valor = None 
            valores.append(valor)
    else:
        valores = [coleta[0] for coleta in coletas]

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
    imagem_grafico = f'/home/allan/pibiti/plataforma_gestao_agropecuaria/app/static/graficos/grafico-{dispositivo_id}-{coluna_dict["nome"]}.png'
    
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
def etapas_experimento(experimento_id):
    permissao_usuario = 'nenhuma'
    for permissao in current_user.permissoes:
        if permissao[0] ==  experimento_id:
            permissao_usuario = permissao
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.etapa WHERE experimento_id = %s ORDER BY ordem", (experimento_id,))
    etapas = cur.fetchall()
    cur.execute("SELECT * FROM api.experimento WHERE id = %s", (experimento_id,))
    experimento = cur.fetchone()
    return render_template('etapas-detalhes.html', experimento_id=experimento_id, experimento=experimento,etapas=etapas,permissao=permissao_usuario, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/inserir', methods=['GET','POST'])
@login_required
def inserir_etapa(experimento_id):
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        status = request.form['status']
        experimento_id = experimento_id
        
        cur = conn.cursor()
        cur.execute("INSERT INTO api.etapa (nome, descricao, status, experimento_id) VALUES (%s, %s, %s, %s)", (nome, descricao, status, experimento_id))
        conn.commit()
        flash('Etapa inserida com sucesso!', 'success')
        return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))
    else:
        return render_template('etapa-inserir.html', experimento_id=experimento_id, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/ordem', methods=['GET'])
@login_required
def ordem_etapa(experimento_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM api.etapa WHERE experimento_id = %s ORDER BY ordem;", (experimento_id,))
    etapas = cur.fetchall()
    return render_template('etapas-ordem.html', etapas=etapas, user=current_user)

@app.route('/detalhes-experimento/<int:experimento_id>/etapas/atualizar_ordem', methods=['POST'])
@login_required
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
def etapa_anexos(experimento_id, etapa_id):
    if request.method == 'POST':
        if 'file' in request.files:
            arquivo = request.files['file']
            descricao = request.form['descricao']
            if arquivo and allowed_file(arquivo.filename):
                nome_arquivo = secure_filename(arquivo.filename)
                caminho_arquivo = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
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
def deletar_etapa(experimento_id, etapa_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.etapa WHERE id = %s", (etapa_id,))
    return redirect(url_for('etapas_experimento', experimento_id=experimento_id, user=current_user))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/detalhes-experimento/etapas/<int:etapa_id>/anexos/<int:anexo_id>/download')
@login_required
def download_anexo(etapa_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()
    caminho_do_arquivo = resultado[0] if resultado else None

    if caminho_do_arquivo:
        return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(caminho_do_arquivo)    )
    else:
        return 'Arquivo não encontrado', 404


@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/anexos/<int:anexo_id>/deletar')
@login_required
def deletar_anexos_etapa(experimento_id,etapa_id, anexo_id):
    cur = conn.cursor()
    cur.execute("SELECT caminho_do_arquivo FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    resultado = cur.fetchone()

    cur.execute("DELETE FROM api.anexos_etapa WHERE id = %s", (anexo_id,))
    conn.commit()
    
    if resultado:
        caminho_do_arquivo = resultado[0]
        if os.path.exists(caminho_do_arquivo):
            os.remove(caminho_do_arquivo)


        return redirect(url_for('etapa_anexos', etapa_id=etapa_id, experimento_id=experimento_id, user=current_user))
    else:
        return 'Arquivo não encontrado', 404


@app.route('/detalhes-experimento/<int:experimento_id>/etapas/<int:etapa_id>/url', methods=['GET','POST'])
@login_required
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
def deletar_url_etapa(experimento_id,etapa_id, url_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM api.urls_etapa WHERE id = %s", (url_id,))
    conn.commit()

    return redirect(url_for('etapa_url', etapa_id=etapa_id, experimento_id=experimento_id, user=current_user))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002,threaded=True)
    #app.run(debug=True, threaded=True, port=5002)

