# app/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)  # igual que tu esquema actual
    rol = db.Column(db.String(20), nullable=False)

    actas = db.relationship("Acta", back_populates="usuario", cascade="all, delete-orphan")
    informes = db.relationship("Informe", back_populates="usuario", cascade="all, delete-orphan")
    reportes = db.relationship("Reporte", back_populates="usuario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Usuario {self.email}>"

class Acta(db.Model):
    __tablename__ = "actas"
    id = db.Column(db.Integer, primary_key=True)
    asunto = db.Column(db.Text, nullable=False)
    observaciones = db.Column(db.Text)
    fecha = db.Column(db.Date)
    hora = db.Column(db.Time)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)

    usuario = db.relationship("Usuario", back_populates="actas")

class Informe(db.Model):
    __tablename__ = "informes"
    id = db.Column(db.Integer, primary_key=True)
    asunto = db.Column(db.Text, nullable=False)
    observaciones = db.Column(db.Text)
    fecha = db.Column(db.Date)
    hora = db.Column(db.Time)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)

    usuario = db.relationship("Usuario", back_populates="informes")

class Reporte(db.Model):
    __tablename__ = "reportes"
    id = db.Column(db.Integer, primary_key=True)
    asunto = db.Column(db.Text, nullable=False)
    observaciones = db.Column(db.Text)
    fecha = db.Column(db.Date)
    hora = db.Column(db.Time)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)

    usuario = db.relationship("Usuario", back_populates="reportes")
