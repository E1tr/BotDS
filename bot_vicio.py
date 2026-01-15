import discord
import os
import requests
from discord.ext import commands
from dotenv import load_dotenv
from pymongo import MongoClient
from flask import Flask
from threading import Thread

# 1. Cargar configuración
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
STEAM_API_KEY = os.getenv('STEAM_API_KEY')
MONGO_URI = os.getenv('MONGO_URI')

# --- PRUEBA DE CONEXIÓN ROBUSTA ---
print("🔌 Conectando con la base de datos...")
try:
    # Si MONGO_URI está vacío, el MongoClient lanzará error antes de intentar localhost
    if not MONGO_URI:
        raise ValueError("No se encontró MONGO_URI en el archivo .env")
        
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # El 'ping' confirma que Atlas nos ha dejado entrar
    client.admin.command('ping')
    db = client['code_and_canas_db']
    coleccion = db['puntos_karma']
    print("✅ Conexión a MongoDB Atlas establecida con éxito")
except Exception as e:
    print(f"❌ ERROR CRÍTICO DE CONEXIÓN: {e}")
    print("Asegúrate de que MONGO_URI en el .env sea correcto y que tu IP esté permitida en Atlas.")

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Eventos
@bot.event
async def on_ready():
    print(f'✅ Bot online como {bot.user}')

# --- SISTEMA DE KARMA (MONGODB) ---
@bot.command(aliases=['ty', 'carry'])
async def gracias(ctx, el_pro: discord.Member, *, motivo: str = "ser un grande"):
    if el_pro == ctx.author:
        await ctx.send("¡No te des las gracias a ti mismo, fantasma! 🤡")
        return

    pro_id = str(el_pro.id)
    
    try:
        usuario = coleccion.find_one({"_id": pro_id})
        
        if not usuario:
            usuario = {"_id": pro_id, "puntos": 0, "logros": []}
        
        usuario["puntos"] += 1
        usuario["logros"].append(motivo)
        if len(usuario["logros"]) > 3: 
            usuario["logros"].pop(0)

        coleccion.replace_one({"_id": pro_id}, usuario, upsert=True)
        await ctx.send(f"💎 **{el_pro.display_name}** ha recibido un punto de Carry de parte de {ctx.author.mention}.\n**Motivo:** *{motivo}*")
    except Exception as e:
        await ctx.send("⚠️ Error al conectar con la base de datos. Avisa al admin.")
        print(f"Error en !gracias: {e}")

@bot.command()
async def top(ctx):
    try:
        usuarios = list(coleccion.find().sort("puntos", -1).limit(5))
        
        if not usuarios:
            await ctx.send("Aquí no ayuda ni Dios. 💀")
            return

        embed = discord.Embed(title="🏆 EL OLIMPO DE CODE & CAÑAS 🏆", color=discord.Color.gold())
        
        for i, info in enumerate(usuarios):
            try:
                user = await bot.fetch_user(int(info["_id"]))
                nombre = user.name
            except:
                nombre = f"User_{info['_id'][-4:]}"
                
            medalla = ["🥇", "🥈", "🥉", "🎖️", "🎖️"][i]
            logros_texto = "\n".join([f"• {l}" for l in info.get('logros', [])])
            
            embed.add_field(
                name=f"{medalla} {nombre} - {info['puntos']} puntos",
                value=f"**Últimas hazañas:**\n{logros_texto if logros_texto else 'Ayudando en las sombras'}",
                inline=False
            )
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error en !top: {e}")

# --- COMANDOS DE JUEGOS ---
@bot.command()
async def stats_valo(ctx, nick: str, tag: str):
    url = f"https://api.henrikdev.xyz/valorant/v1/lastranked/{nick}/{tag}"
    res = requests.get(url)
    if res.status_code == 200:
        d = res.json()['data']
        k, det, a = d['stats']['kills'], d['stats']['deaths'], d['stats']['assists']
        mapa = d['meta']['map']['name']
        msg = "🔥 ¡Vaya carry!" if k > det else "💀 Fardo detectado."
        await ctx.send(f"📊 **Última de {nick}#{tag}** en **{mapa}**: {k}/{det}/{a}. Veredicto: {msg}")
    else:
        await ctx.send("No encuentro a ese nota en Valorant.")

@bot.command()
async def stats_cs(ctx, steam_id: str):
    if not STEAM_API_KEY:
        await ctx.send("Bro, no has configurado la API Key de Steam en el .env")
        return
    url = f"http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?appid=730&key={STEAM_API_KEY}&steamid={steam_id}"
    res = requests.get(url)
    if res.status_code == 200:
        s = {i['name']: i['value'] for i in res.json()['playerstats']['stats']}
        k, d = s.get('total_kills', 0), s.get('total_deaths', 0)
        await ctx.send(f"🔫 **Stats CS2**: {k} bajas totales. K/D: {round(k/d, 2) if d>0 else 0}")
    else:
        await ctx.send("Error con Steam. ¿Perfil público?")

@bot.command()
@commands.has_permissions(administrator=True)
async def reset_mes(ctx):
    coleccion.delete_many({})
    await ctx.send("🧹 Marcador de MongoDB limpiado.")

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()



keep_alive()

bot.run(TOKEN)