
from flask import Flask, render_template, request, url_for, redirect, flash
#importo modulo mysql
from flask_mysqldb import MySQL
import telnetlib
import functools
import time
import ctypes
import webbrowser
import sys

def checkpname(mess):
    if b"no file" in mess:
        return "No se está imprimiendo"
    elif b"Current file" in mess:
        text = mess.decode("utf-8")[1:-3].split("file: ",1)[1]
        return "Se está imprimiendo: " + text +"\n"
    else:
        return "Impresora no responde"

def checkprint(mess):
    if b"no file" in mess:
        return "notp"
    elif b"Current file" in mess:
        return "isp"
    else:
        return "else"

def readm27(mess):

        if b"Not SD printing" in mess:
            return "notp",0.0
        #elif b"T:" in mess :
        #    return "heat",0.0
        elif b"SD printing" in mess:
            text=mess.decode("utf-8")
            percentext=""
            for l in text:
                if (l>='0' and l<='9') or l=="/":
                    percentext+=l
            temp=percentext.split("/")
            return "print",100*int(temp[0])/int(temp[1])
        else:
            return "else",0.0
            

def checkanswer(mess):
        if b"Resend" in mess:
            return True
        elif b"ok" in mess:
            return False
        elif b"T:" in mess :
            print("Actualmente la impresora esta calentando e ignorara otros comandos, espere un minuto")
            for n in range(6):
                time.sleep(10)
                print(str((n+1)*10)+" segundos pasados...")
            print("Listo")
            return True
        else:
            return True


app = Flask(__name__)
#my sql connection
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'usuario'
app.config['MYSQL_PASSWORD'] = '123'
app.config['MYSQL_DB'] = 'flaskprinters'

mysql = MySQL(app)

#sesion

app.secret_key = 'mysecretkey'

#ruta para index
@app.route('/')
def Index():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras')
    data = cur.fetchall()
    return render_template('index.html', impresoras = data)

#ruta para formulario
@app.route('/formulario')
def formulario():
    return render_template('formulario.html')

#ruta para agregar una impresora
@app.route('/add_printer', methods = ['POST']) # como agrego ocupa metodo post
def add_printer():
    if request.method == 'POST': # agrega base de datos
        name= request.form['name']
        ip= request.form['ip']
        ip_publica = request.form['ip_publica']
        boquilla = request.form['boquilla']
        cama = request.form['cama']
        filamento = request.form['filamento']
        color_filamento = request.form['color_filamento']
        estado = "Impresora disponible"
        cur = mysql.connection.cursor()
        if name == '' or ip == '' or ip_publica == '':
            flash('Estos campos son obligatorios: Nombre, Ip, Ip pública')
            return redirect(url_for('formulario'))

        else:
            cur.execute('INSERT INTO impresoras (name, ip, ip_publica, boquilla, cama, filamento, color_filamento, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',(name, ip, ip_publica, boquilla, cama, filamento, color_filamento, estado))
            mysql.connection.commit()
            flash('Impresora agregada con éxito')
            return redirect(url_for('Index'))
    

#ruta para obtener id de una impresora una impresora
@app.route('/edit/<id>')
def get_printer(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    return render_template('edit.html', datos = data[0])

@app.route('/panel/<id>')
def panel(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    host = data[0][2] # data[0][2]= ip-privada data[0][3] = ip-publica
    port = "8888"
    conected=False
    try:
        tn = telnetlib.Telnet(host,port)
        print("conectado")
        conected=True
    except:
        flash("La impresora está apagada")
    if conected:
        send=1
        while send:
            print("M27 C")
            tn.write(b"M27 C\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)
            send=checkanswer(msj)
        est=checkprint(msj)
        if est == "notp":
            estado = "Impresora disponible"
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE impresoras
                SET estado = %s
                WHERE id = %s
            """, (estado, id))
            mysql.connection.commit()
            cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
            data = cur.fetchall()
            #tn.close()
            return render_template('panel.html', datos = data[0])
        else:
            estado = "Imprimiendo.."
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE impresoras
                SET estado = %s
                WHERE id = %s
            """, (estado, id))
            mysql.connection.commit()
            cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
            data = cur.fetchall()
            #tn.close()
            return render_template('panel.html', datos = data[0])
    return redirect(url_for('Index'))

@app.route('/isabort/<id>')
def isabort(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    host = data[0][2]
    print(host)
    port = "8888"
    conected=False
    try:
        tn = telnetlib.Telnet(host,port)
        print("conectado")
        conected=True
    except:
        flash("Hubo un error") 
    if (conected):
        send=1
        while send:
            tn.write(b"M27\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)          
            send=checkanswer(msj)
        est1,per=readm27(msj)      
        send=1
        while send:
            tn.write(b"M27 C\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)          
            send=checkanswer(msj)
        est2=checkprint(msj)
        if est1=="notp" and est2=="isp":
            flash("No se puede abortar mientras este pausado")
        else:
            send=1
            while send:
                tn.write(b"M524\n")
                msj = tn.read_until(b'ok',timeout=10)
                print(msj)          
                send=checkanswer(msj)
            flash("Impresión abortada\n")
        #tn.close()
    return render_template('panel.html', datos=data[0])


    
    
#ruta para editar impresora
@app.route('/update/<id>', methods = ['POST'])
def update_printer(id):
    if request.method == 'POST':
        name = request.form['name']
        ip = request.form['ip']
        ip_publica= request.form['ip_publica']
        boquilla = request.form['boquilla']
        cama = request.form['cama']
        filamento = request.form['filamento']
        color_filamento = request.form ['color_filamento']
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE impresoras
            SET name = %s,
                ip = %s,
                ip_publica = %s,
                boquilla = %s,
                cama = %s,
                filamento = %s,
                color_filamento = %s
            WHERE id = %s
        """, (name, ip, ip_publica, boquilla, cama, filamento, color_filamento, id))
        mysql.connection.commit()
        flash('Impresora editada correctamente')
        return redirect(url_for('Index'))

#ruta para eliminar una impresora
@app.route('/delete/<string:id>')
def delete_printer(id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM impresoras WHERE id = {0}'.format(id)) #posicion 0 esta relacionada con la tabla de php
    mysql.connection.commit()
    flash('Impresora Eliminada Correctamente')
    return redirect(url_for('Index'))

@app.route('/progreso/<string:id>')
def progreso(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    host = data[0][2] # data[0][2]= ip-privada data[0][3] = ip-publica
    port = "8888"
    conected=False
    try:
        tn = telnetlib.Telnet(host,port)
        print("conectado")
        conected=True
    except:
        flash("La impresora está apagada")
    if conected:
        send=1
        while send:
            print("M27")
            tn.write(b"M27\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)
            send=checkanswer(msj)
        est,per=readm27(msj)
        if est == "print":
            porcentaje = str(int(per))
            flash("Porcentaje Impresión: "+porcentaje+"%\n")
            #tn.close()
            return render_template('panel.html', datos = data[0])
          
        else:
            #tn.close()
            flash("No se está imprimiendo")
            return render_template('panel.html', datos = data[0])

@app.route('/pausar/<string:id>')
def pausar(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    host = data[0][2]
    print(host)
    port = "8888"
    conected=False
    try:
        tn = telnetlib.Telnet(host,port)
        print("conectado")
        conected=True
    except:
        flash("La impresora no está conectada") 
    if conected:
        send=1        
        while send:
            tn.write(b"M27 C\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)          
            send=checkanswer(msj)
        est=checkprint(msj)
        if est=="isp":
            send=1        
            while send:
                tn.write(b"M25\n")
                msj = tn.read_until(b'ok',timeout=10)
                print(msj)          
                send=checkanswer(msj)
            flash("Impresión pausada\n")
        elif est=="notp":   
            flash("No se está imprimiendo nada")
        else:
            flash("No se pudo conectar")
        
    #tn.close()
    return render_template('panel.html', datos=data[0])

@app.route('/resumir/<string:id>')
def resumir(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    host = data[0][2]
    print(host)
    port = "8888"
    conected=False
    try:
        tn = telnetlib.Telnet(host,port)
        print("conectado")
        conected=True
    except:
        flash("La impresora no está conectada") 
    if conected:
        send=1
        while send:
            tn.write(b"M27 C\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)          
            send=checkanswer(msj)
        est=checkprint(msj)
        if est=="isp":
            send=1        
            while send:
                tn.write(b"M24\n")
                msj = tn.read_until(b'ok',timeout=10)
                print(msj)          
                send=checkanswer(msj)
            flash("Impresion reanudada\n")
        elif est=="notp":   
            flash("No se está imprimiendo")
        else:
            flash("No se pudo conectar")
        
    #tn.close()
    return render_template('panel.html', datos=data[0])
    
@app.route('/archivo/<string:id>')
def archivo(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM impresoras WHERE id = %s', [id])
    data = cur.fetchall()
    host = data[0][2]
    print(host)
    port = "8888"
    conected=False
    try:
        tn = telnetlib.Telnet(host,port)
        print("conectado")
        conected=True
    except:
        flash("La impresora no está conectada") 
    if conected:
        send=1
        while send:
            tn.write(b"M27 C\n")
            msj = tn.read_until(b'ok',timeout=10)
            print(msj)          
            send=checkanswer(msj)
        flash(checkpname(msj))
        
    #tn.close()
    return render_template('panel.html', datos=data[0])

#si existe se abre el servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


