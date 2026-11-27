using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

// Minijuego de PixelLang: el caballero, que controla el jugador, contra un slime. Los dos son
// personajes de ejemplos/juego.pxl, compilados juntos en pixellang.dll (índices 0 y 1).
//
// Este script es el cuerpo de los personajes y la biblioteca es su cerebro. El script convierte
// lo que pasa en el juego en eventos (una tecla, un contacto, el final de una animación) y
// dibuja lo que la biblioteca decide: el estado y los atributos. Las reglas de PixelLang no
// están aquí: si un evento no tiene transición en el estado actual, la biblioteca lo ignora y
// la escena solo lo muestra. Abajo se ve la función de transición δ de cada personaje con la
// transición que se acaba de tomar.
//
// Con -captura <carpeta>, una partida de demostración se juega sola (un guion pulsa las teclas)
// y se guarda un cuadro por cada 1/30 de segundo en esa carpeta, para grabar el video.
public class JuegoPixelLang : MonoBehaviour
{
    // Duración de la animación de un estado y evento que el juego envía cuando termina,
    // como un Animation Event de Unity
    struct Animacion
    {
        public float duracion;
        public string evento;
        public Animacion(float duracion, string evento) { this.duracion = duracion; this.evento = evento; }
    }

    static readonly Dictionary<string, Animacion> AnimacionesCaballero = new Dictionary<string, Animacion>
    {
        { "Atacando", new Animacion(0.45f, "fin_ataque") },
        { "Saltando", new Animacion(0.85f, "aterrizar") },
        { "Aturdido", new Animacion(0.9f, "fin_aturdimiento") },
    };

    static readonly Dictionary<string, Animacion> AnimacionesSlime = new Dictionary<string, Animacion>
    {
        { "Aturdido", new Animacion(0.9f, "fin_aturdimiento") },
    };

    // Ajustes del motor: posiciones, distancias y velocidades del movimiento
    const float XCaballero = -3.2f;
    const float VisionSlime = 7.5f, PerdidaSlime = 9.5f;
    const float VelocidadPatrulla = 1.0f, VelocidadPersecucion = 1.9f;
    const float PatrullaIzquierda = 4.0f, PatrullaDerecha = 6.5f;
    const float Contacto = 1.15f;
    const float AlcanceBase = 1.6f;
    const float AlturaPisoton = 0.6f;
    const float EscalaSalto = 0.9f;       // unidades del mundo por cada unidad del atributo y

    static readonly Color Naranja = new Color(1f, 0.62f, 0.25f);
    static readonly Color Gris = new Color(0.62f, 0.65f, 0.72f);

    public ActorPixelLang Caballero { get; private set; }
    public ActorPixelLang Slime { get; private set; }
    public bool FinDePartida
    {
        get { return Caballero != null && (Caballero.EnEstadoFinal || Slime.EnEstadoFinal); }
    }

    string problema = "";
    float xSlime, empujeSlime, alturaCaballero, finPartida = -1f;
    int direccionPatrulla = 1;
    bool slimeVe, golpeDeEsteAtaque, demostracion;
    float cierreCaballero = -1f, cierreSlime = -1f;
    string carpetaCaptura;
    int cuadro;

    Transform caballeroBase, slimeBase;
    SpriteRenderer caballeroFigura, slimeFigura, tajo;
    readonly List<Transform> estrellasCaballero = new List<Transform>();
    readonly List<Transform> estrellasSlime = new List<Transform>();

    class Aviso
    {
        public string texto;
        public Vector3 posicion;
        public float inicio;
        public Color color;
        public bool delCaballero;
        public float subida;      // los avisos anteriores suben para dejar lugar al nuevo
    }
    readonly List<Aviso> avisos = new List<Aviso>();

    void Start()
    {
        PrepararEscena();
        try
        {
            var mapa = MapaPixelLang.Cargar();
            Caballero = new ActorPixelLang(mapa.Personaje("Caballero"));
            Slime = new ActorPixelLang(mapa.Personaje("Slime"));
            Reiniciar();
        }
        catch (Exception e)
        {
            Caballero = Slime = null;
            problema = "No se pudo usar la biblioteca pixellang: " + e.Message;
            Debug.LogError(problema);
            return;
        }
        string[] args = Environment.GetCommandLineArgs();
        int k = Array.IndexOf(args, "-captura");
        if (k >= 0 && k + 1 < args.Length)
        {
            carpetaCaptura = args[k + 1];
            Directory.CreateDirectory(carpetaCaptura);
            Time.captureFramerate = 30;
            StartCoroutine(Capturar());
            IniciarDemostracion();
        }
    }

    public void Reiniciar()
    {
        if (Caballero == null)
            return;
        Caballero.Iniciar(Time.time);
        Slime.Iniciar(Time.time);
        xSlime = 5.5f;
        empujeSlime = 0f;
        direccionPatrulla = 1;
        slimeVe = false;
        golpeDeEsteAtaque = false;
        alturaCaballero = 0f;
        finPartida = -1f;
        cierreCaballero = cierreSlime = -1f;
        avisos.Clear();
    }

    // Eventos ---------------------------------------------------------------------------

    // Todos los eventos pasan por aquí: van a la biblioteca y quedan como aviso en pantalla
    int Enviar(ActorPixelLang actor, string evento, string tecla = null)
    {
        int tomada = actor.Enviar(evento, Time.time);
        bool esCaballero = actor == Caballero;
        Vector3 sobre = esCaballero ? caballeroBase.position + new Vector3(0f, 3.15f, 0f)
                                    : slimeBase.position + new Vector3(0f, 2.3f, 0f);
        string texto = (tecla != null ? "[" + tecla + "] " : "") + evento + (tomada < 0 ? ": ignorado" : "");
        foreach (var anterior in avisos)
            if (anterior.delCaballero == esCaballero)
                anterior.subida += 20f;
        avisos.Add(new Aviso
        {
            texto = texto, posicion = sobre, inicio = Time.time, color = tomada < 0 ? Naranja : Color.white,
            delCaballero = esCaballero,
        });
        if (esCaballero && tomada >= 0 && Caballero.Delta[tomada].destino == "Atacando")
            golpeDeEsteAtaque = false;     // cada ataque puede golpear una vez
        return tomada;
    }

    // Lo que hace una tecla: enviar un evento al caballero
    public void Pulsar(string evento, string tecla)
    {
        if (Caballero != null && !FinDePartida)
            Enviar(Caballero, evento, tecla);
    }

    float Distancia() { return xSlime - XCaballero; }

    // La espada llega más lejos cuanto mayor es la velocidad, un atributo que calcula la
    // biblioteca al entrar a Atacando (1.5 con vida >= 50 y 1.0 con menos)
    float Alcance() { return AlcanceBase + 0.6f * (float)Caballero.Valor("velocidad"); }

    void Update()
    {
        if (Caballero == null)
            return;
        var teclado = Keyboard.current;
        if (teclado != null)
        {
            if (teclado.rKey.wasPressedThisFrame)
                Reiniciar();
            if (teclado.tabKey.wasPressedThisFrame)
            {
                SceneManager.LoadScene("DemoPixelLang");
                return;
            }
            if (!demostracion)
            {
                if (teclado.spaceKey.wasPressedThisFrame || teclado.wKey.wasPressedThisFrame)
                    Pulsar("saltar", "Espacio");
                if (teclado.jKey.wasPressedThisFrame || teclado.kKey.wasPressedThisFrame)
                    Pulsar("atacar", "J");
            }
        }
        if (!FinDePartida)
        {
            FinDeAnimaciones();
            MoverSlime(Time.deltaTime);
            Contactos();
        }
        else if (finPartida < 0f)
            finPartida = Time.time;
        Dibujar(Time.deltaTime);
    }

    void FinDeAnimaciones()
    {
        Animacion a;
        if (AnimacionesCaballero.TryGetValue(Caballero.Estado, out a)
            && Time.time - Caballero.MomentoTransicion >= a.duracion && cierreCaballero != Caballero.MomentoTransicion)
        {
            cierreCaballero = Caballero.MomentoTransicion;
            Enviar(Caballero, a.evento);
        }
        if (AnimacionesSlime.TryGetValue(Slime.Estado, out a)
            && Time.time - Slime.MomentoTransicion >= a.duracion && cierreSlime != Slime.MomentoTransicion)
        {
            cierreSlime = Slime.MomentoTransicion;
            Enviar(Slime, a.evento);
        }
    }

    void MoverSlime(float dt)
    {
        // empuje de un golpe
        xSlime += empujeSlime * dt;
        empujeSlime = Mathf.MoveTowards(empujeSlime, 0f, 12f * dt);
        // Percepción: el juego avisa cuando el slime empieza a ver al caballero o lo pierde
        bool ve = slimeVe ? Distancia() <= PerdidaSlime : Distancia() <= VisionSlime;
        if (ve != slimeVe)
        {
            slimeVe = ve;
            Enviar(Slime, ve ? "ver_jugador" : "perder_jugador");
        }
        // Cómo se mueve en cada estado (el estado lo decide la biblioteca)
        if (Slime.Estado == "Patrulla")
        {
            xSlime += direccionPatrulla * VelocidadPatrulla * dt;
            if (xSlime < PatrullaIzquierda) direccionPatrulla = 1;
            if (xSlime > PatrullaDerecha) direccionPatrulla = -1;
        }
        else if (Slime.Estado == "Persecucion" && empujeSlime < 0.01f)
            xSlime -= VelocidadPersecucion * dt;
        xSlime = Mathf.Clamp(xSlime, XCaballero + 0.6f, 7.6f);
    }

    void Contactos()
    {
        if (Slime.EnEstadoFinal)
            return;
        // La espada alcanza al slime
        if (Caballero.Estado == "Atacando" && !golpeDeEsteAtaque && Distancia() <= Alcance())
        {
            golpeDeEsteAtaque = true;
            Enviar(Slime, "recibir_golpe");
            empujeSlime = 7f;
            return;
        }
        if (Distancia() > Contacto || empujeSlime > 0.5f)
            return;
        if (alturaCaballero >= AlturaPisoton)
        {
            // el caballero cae sobre el slime
            Enviar(Slime, "recibir_golpe");
            empujeSlime = 7f;
        }
        else
        {
            Enviar(Caballero, "recibir_golpe");
            empujeSlime = 6f;      // el slime rebota
        }
    }

    // Guion de la partida de demostración: solo pulsa teclas, como lo haría un jugador
    public void IniciarDemostracion()
    {
        demostracion = true;
        Reiniciar();
        StartCoroutine(Demostracion());
    }

    IEnumerator Demostracion()
    {
        // 1. Ataca cuando el slime está cerca (con velocidad 1.5, la espada llega a 2.5)
        yield return new WaitUntil(() => Slime.Estado == "Persecucion" && Distancia() <= 2.4f);
        Pulsar("atacar", "J");
        // 2. Deja que el slime lo toque y, aturdido, intenta atacar: la biblioteca lo ignora
        yield return new WaitUntil(() => Caballero.Estado == "Aturdido");
        yield return new WaitForSeconds(0.35f);
        Pulsar("atacar", "J");
        // 3. Salta y cae sobre el slime
        yield return new WaitUntil(() => Caballero.Estado == "Reposo" && Slime.Estado == "Persecucion"
                                         && Distancia() <= 2.2f);
        Pulsar("saltar", "Espacio");
        // 4. Último golpe: con vida 0, la guarda lleva al slime a su estado final
        yield return new WaitUntil(() => Caballero.Estado == "Reposo" && Slime.Estado == "Persecucion"
                                         && Distancia() <= 2.4f);
        Pulsar("atacar", "J");
    }

    IEnumerator Capturar()
    {
        while (true)
        {
            yield return new WaitForEndOfFrame();
            var imagen = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(carpetaCaptura, $"cuadro_{cuadro++:D5}.png"), imagen.EncodeToPNG());
            Destroy(imagen);
            if ((finPartida > 0f && Time.time >= finPartida + 4f) || Time.time > 90f)
                break;
        }
        Application.Quit();
    }

    // Escena -----------------------------------------------------------------------------

    static SpriteRenderer Figura(string nombre, Sprite sprite, Vector3 posicion, Vector3 escala, int orden,
                                 Transform padre = null)
    {
        var figura = new GameObject(nombre).AddComponent<SpriteRenderer>();
        if (padre != null)
            figura.transform.SetParent(padre, false);
        figura.sprite = sprite;
        figura.transform.localPosition = posicion;
        figura.transform.localScale = escala;
        figura.sortingOrder = orden;
        return figura;
    }

    void PrepararEscena()
    {
        var camara = Camera.main;
        if (camara == null)
        {
            camara = new GameObject("Main Camera").AddComponent<Camera>();
            camara.tag = "MainCamera";
        }
        camara.orthographic = true;
        camara.orthographicSize = 4.6f;
        camara.transform.position = new Vector3(0f, 1.64f, -10f);
        camara.clearFlags = CameraClearFlags.SolidColor;
        camara.backgroundColor = new Color(0.10f, 0.12f, 0.19f);

        var azar = new System.Random(5);
        var punto = DibujosPixelLang.DeColor(new Color(0.85f, 0.88f, 1f, 0.7f));
        for (int i = 0; i < 28; i++)
            Figura("Estrella del cielo", punto, new Vector3((float)azar.NextDouble() * 18f - 9f,
                   2.5f + (float)azar.NextDouble() * 1.9f, 0f), Vector3.one * 0.06f, -5);
        Figura("Colinas lejanas", DibujosPixelLang.Colinas(new Color(0.14f, 0.17f, 0.26f), 7),
               new Vector3(0f, -0.3f, 0f), Vector3.one, -4);
        Figura("Colinas", DibujosPixelLang.Colinas(new Color(0.17f, 0.22f, 0.30f), 41),
               new Vector3(2f, -0.6f, 0f), new Vector3(1f, 0.6f, 1f), -3);
        Figura("Suelo", DibujosPixelLang.DeColor(new Color(0.27f, 0.21f, 0.16f)),
               new Vector3(0f, -2.5f, 0f), new Vector3(40f, 5f, 1f), 0);
        Figura("Pasto", DibujosPixelLang.DeColor(new Color(0.30f, 0.56f, 0.28f)),
               new Vector3(0f, -0.1f, 0f), new Vector3(40f, 0.2f, 1f), 1);

        caballeroBase = new GameObject("Caballero").transform;
        caballeroFigura = Figura("Dibujo", DibujosPixelLang.Caballero(), Vector3.zero, Vector3.one, 3, caballeroBase);
        tajo = Figura("Tajo", DibujosPixelLang.Tajo(), new Vector3(0.95f, 1.0f, 0f), Vector3.one, 4, caballeroBase);
        slimeBase = new GameObject("Slime").transform;
        slimeFigura = Figura("Dibujo", DibujosPixelLang.Slime(), Vector3.zero, Vector3.one, 3, slimeBase);
        var estrella = DibujosPixelLang.Estrella();
        for (int i = 0; i < 3; i++)
        {
            estrellasCaballero.Add(Figura("Estrella", estrella, Vector3.zero, Vector3.one, 5).transform);
            estrellasSlime.Add(Figura("Estrella", estrella, Vector3.zero, Vector3.one, 5).transform);
        }
    }

    void Dibujar(float dt)
    {
        if (Caballero == null)
            return;
        float ahora = Time.time;
        // Caballero: la altura del salto sale del atributo y; la embestida, de velocidad
        if (Caballero.Estado == "Saltando")
        {
            float f = Mathf.Clamp01((ahora - Caballero.MomentoTransicion) / AnimacionesCaballero["Saltando"].duracion);
            alturaCaballero = (float)Caballero.Valor("y") * EscalaSalto * 4f * f * (1f - f);
        }
        else
            alturaCaballero = Mathf.MoveTowards(alturaCaballero, 0f, 9f * dt);
        float embestida = 0f, faseAtaque = 0f;
        if (Caballero.Estado == "Atacando")
        {
            faseAtaque = Mathf.Clamp01((ahora - Caballero.MomentoTransicion) / AnimacionesCaballero["Atacando"].duracion);
            embestida = (float)Caballero.Valor("velocidad") * 0.5f * Mathf.Sin(faseAtaque * Mathf.PI);
        }
        caballeroBase.position = new Vector3(XCaballero + embestida, alturaCaballero, 0f);
        bool caido = Caballero.EnEstadoFinal;
        caballeroFigura.transform.localRotation = Quaternion.Euler(0f, 0f, caido ? 90f : 0f);
        caballeroFigura.transform.localPosition = caido ? new Vector3(1f, 0.75f, 0f) : Vector3.zero;
        bool parpadeo = Caballero.Estado == "Aturdido" && Mathf.Repeat(ahora * 8f, 1f) < 0.5f;
        caballeroFigura.color = caido ? new Color(0.55f, 0.55f, 0.6f) : parpadeo ? new Color(1f, 0.85f, 0.45f) : Color.white;
        tajo.enabled = Caballero.Estado == "Atacando";
        tajo.color = new Color(1f, 1f, 1f, 1f - faseAtaque * 0.8f);
        tajo.transform.localScale = new Vector3(0.7f + 0.5f * faseAtaque, 1f, 1f);
        Estrellas(estrellasCaballero, caballeroBase.position + new Vector3(0f, 2.15f, 0f), Caballero.Estado == "Aturdido");

        // Slime: rebota al moverse, se aplasta con un golpe y queda plano en su estado final
        float salto = 0f, escalaY = 1f;
        if (Slime.Estado == "Patrulla" || Slime.Estado == "Persecucion")
        {
            float fase = ahora * (Slime.Estado == "Persecucion" ? 7f : 4.5f);
            salto = Mathf.Abs(Mathf.Sin(fase)) * 0.35f;
            escalaY = 1f + 0.08f * Mathf.Cos(2f * fase);
        }
        else if (Slime.EnEstadoFinal)
            escalaY = 0.3f;
        else
            escalaY = 0.65f;
        slimeBase.position = new Vector3(xSlime, salto, 0f);
        slimeFigura.transform.localScale = new Vector3(1f + 0.5f * (1f - escalaY), escalaY, 1f);
        slimeFigura.color = Slime.EnEstadoFinal ? new Color(0.5f, 0.55f, 0.5f)
                          : Slime.Estado == "Persecucion" ? new Color(1f, 0.82f, 0.82f) : Color.white;
        Estrellas(estrellasSlime, slimeBase.position + new Vector3(0f, 1.25f, 0f), Slime.Estado == "Aturdido");
    }

    static void Estrellas(List<Transform> estrellas, Vector3 centro, bool visibles)
    {
        for (int i = 0; i < estrellas.Count; i++)
        {
            estrellas[i].gameObject.SetActive(visibles);
            float angulo = Time.time * 5f + i * Mathf.PI * 2f / estrellas.Count;
            estrellas[i].position = centro + new Vector3(Mathf.Cos(angulo) * 0.6f, Mathf.Sin(angulo) * 0.18f, 0f);
        }
    }

    // Interfaz ------------------------------------------------------------------------

    GUIStyle titulo, subtitulo, nombre, estadoGrande, texto, pequeno, pequenoDerecha, celda, aviso,
             etiqueta, banner, panel, panelOpaco;
    Texture2D blanco;

    static Texture2D Textura(Color color)
    {
        var t = new Texture2D(1, 1);
        t.SetPixel(0, 0, color);
        t.Apply();
        return t;
    }

    void Estilos()
    {
        if (titulo != null)
            return;
        float s = Screen.height / 720f;
        blanco = Textura(Color.white);
        panel = new GUIStyle { normal = { background = Textura(new Color(0.04f, 0.05f, 0.08f, 0.84f)) } };
        panelOpaco = new GUIStyle { normal = { background = Textura(new Color(0.05f, 0.06f, 0.09f, 0.97f)) } };
        GUIStyle Crear(int tam, FontStyle estilo, TextAnchor alineacion)
        {
            var g = new GUIStyle(GUI.skin.label)
            {
                fontSize = Mathf.RoundToInt(tam * s),
                fontStyle = estilo,
                alignment = alineacion,
                wordWrap = false,
                clipping = TextClipping.Overflow,
            };
            g.normal.textColor = Color.white;
            return g;
        }
        titulo = Crear(22, FontStyle.Bold, TextAnchor.UpperCenter);
        subtitulo = Crear(14, FontStyle.Normal, TextAnchor.UpperCenter);
        subtitulo.normal.textColor = new Color(0.78f, 0.82f, 0.9f);
        nombre = Crear(18, FontStyle.Bold, TextAnchor.UpperLeft);
        estadoGrande = Crear(28, FontStyle.Bold, TextAnchor.UpperLeft);
        texto = Crear(15, FontStyle.Normal, TextAnchor.UpperLeft);
        pequeno = Crear(13, FontStyle.Normal, TextAnchor.UpperLeft);
        pequeno.normal.textColor = Gris;
        pequenoDerecha = Crear(13, FontStyle.Normal, TextAnchor.UpperRight);
        pequenoDerecha.normal.textColor = Gris;
        celda = Crear(13, FontStyle.Normal, TextAnchor.UpperLeft);
        aviso = Crear(15, FontStyle.Bold, TextAnchor.MiddleCenter);
        etiqueta = Crear(17, FontStyle.Bold, TextAnchor.MiddleCenter);
        banner = Crear(34, FontStyle.Bold, TextAnchor.UpperCenter);
    }

    void OnGUI()
    {
        Estilos();
        float s = Screen.height / 720f;
        if (problema != "")
        {
            GUI.Label(new Rect(30 * s, 30 * s, Screen.width - 60 * s, 200 * s), problema,
                      new GUIStyle(texto) { wordWrap = true });
            return;
        }
        if (Caballero == null)
            return;
        Tarjeta(new Rect(20 * s, 16 * s, 410 * s, 108 * s), Caballero, 100, s);
        Tarjeta(new Rect(Screen.width - 430 * s, 16 * s, 410 * s, 108 * s), Slime, 30, s);
        float cx = Screen.width / 2f;
        GUI.Label(new Rect(cx - 210 * s, 20 * s, 420 * s, 30 * s), "PixelLang en Unity", titulo);
        GUI.Label(new Rect(cx - 210 * s, 52 * s, 420 * s, 22 * s), "El juego envía los eventos; pixellang.dll decide el estado", subtitulo);
        GUI.Label(new Rect(cx - 210 * s, 78 * s, 420 * s, 22 * s),
                  demostracion ? "Partida de demostración: un guion pulsa las teclas"
                               : "Espacio: saltar     J: atacar     R: reiniciar     Tab: validación",
                  new GUIStyle(pequeno) { alignment = TextAnchor.UpperCenter });

        Etiqueta(caballeroBase.position + new Vector3(0f, 2.6f, 0f), Caballero.Estado, s);
        Etiqueta(slimeBase.position + new Vector3(0f, 1.75f, 0f), Slime.Estado, s);
        Avisos(s);

        TablaDelta(new Rect(20 * s, 524 * s, 610 * s, 186 * s), Caballero, "δ del caballero (personaje 0)", s);
        TablaDelta(new Rect(Screen.width - 630 * s, 524 * s, 610 * s, 186 * s), Slime, "δ del slime (personaje 1)", s);
        if (FinDePartida)
            Banner(s);
    }

    void Tarjeta(Rect r, ActorPixelLang actor, int vidaMaxima, float s)
    {
        GUI.Box(r, GUIContent.none, panel);
        float x = r.x + 16 * s, y = r.y + 10 * s;
        GUI.Label(new Rect(x, y, 200 * s, 24 * s), actor.Datos.nombre, nombre);
        GUI.Label(new Rect(r.xMax - 216 * s, y + 3 * s, 200 * s, 20 * s), "estado y atributos de la DLL", pequenoDerecha);
        var estilo = new GUIStyle(estadoGrande);
        estilo.normal.textColor = actor.EnEstadoFinal ? Naranja : Color.white;
        GUI.Label(new Rect(x, y + 22 * s, 300 * s, 36 * s), actor.Estado, estilo);
        int vida = (int)actor.Valor("vida");
        var barra = new Rect(x, y + 66 * s, 230 * s, 12 * s);
        GUI.DrawTexture(barra, blanco, ScaleMode.StretchToFill, false, 0f, new Color(0.22f, 0.24f, 0.30f), 0f, 0f);
        float parte = Mathf.Clamp01(vida / (float)vidaMaxima);
        var color = parte > 0.5f ? new Color(0.36f, 0.78f, 0.38f) : parte > 0.25f ? new Color(0.95f, 0.75f, 0.25f) : new Color(0.9f, 0.3f, 0.3f);
        GUI.DrawTexture(new Rect(barra.x, barra.y, barra.width * parte, barra.height), blanco, ScaleMode.StretchToFill, false, 0f, color, 0f, 0f);
        GUI.Label(new Rect(barra.xMax + 12 * s, y + 60 * s, 150 * s, 22 * s), "vida " + vida, texto);
        string otros = "";
        for (int a = 0; a < actor.Datos.atributos.Length; a++)
            if (actor.Datos.atributos[a].nombre != "vida")
                otros += actor.Datos.atributos[a].nombre + " " + actor.nativo.Texto(a) + "     ";
        GUI.Label(new Rect(x, y + 82 * s, r.width - 32 * s, 20 * s), otros.TrimEnd(), pequeno);
    }

    void Etiqueta(Vector3 mundo, string estado, float s)
    {
        var p = Camera.main.WorldToScreenPoint(mundo);
        GUI.Label(new Rect(p.x - 120 * s, Screen.height - p.y - 14 * s, 240 * s, 28 * s), estado, etiqueta);
    }

    void Avisos(float s)
    {
        avisos.RemoveAll(a => Time.time - a.inicio > 1.3f);
        foreach (var a in avisos)
        {
            float edad = Time.time - a.inicio;
            var p = Camera.main.WorldToScreenPoint(a.posicion);
            var estilo = new GUIStyle(aviso);
            var c = a.color;
            c.a = Mathf.Clamp01((1.3f - edad) / 0.45f);
            estilo.normal.textColor = c;
            float y = Screen.height - p.y - (edad * 30f + a.subida) * s;
            GUI.Label(new Rect(p.x - 170 * s, y - 12 * s, 340 * s, 24 * s), a.texto, estilo);
        }
    }

    void TablaDelta(Rect r, ActorPixelLang actor, string tituloTabla, float s)
    {
        GUI.Box(r, GUIContent.none, panel);
        float x = r.x + 14 * s, y = r.y + 8 * s;
        GUI.Label(new Rect(x, y, 320 * s, 22 * s), tituloTabla, new GUIStyle(nombre) { fontSize = Mathf.RoundToInt(15 * s) });
        float edadIgnorado = Time.time - actor.MomentoIgnorado;
        if (edadIgnorado < 2.2f)
        {
            var estilo = new GUIStyle(pequenoDerecha) { fontStyle = FontStyle.Bold };
            estilo.normal.textColor = new Color(Naranja.r, Naranja.g, Naranja.b, Mathf.Clamp01((2.2f - edadIgnorado) / 0.6f));
            GUI.Label(new Rect(r.xMax - 334 * s, y + 2 * s, 320 * s, 20 * s), actor.Ignorado, estilo);
        }
        y += 27 * s;
        float fila = 14.6f * s;
        var delta = actor.Delta;
        var activa = new GUIStyle(celda);
        var inactiva = new GUIStyle(celda);
        inactiva.normal.textColor = new Color(0.45f, 0.48f, 0.55f);
        for (int i = 0; i < delta.Length; i++)
        {
            var t = delta[i];
            float yi = y + i * fila;
            if (i == actor.UltimaTransicion)
            {
                float brillo = Mathf.Clamp01(1.8f - (Time.time - actor.MomentoTransicion));
                if (brillo > 0f)
                    GUI.DrawTexture(new Rect(r.x + 6 * s, yi - 1 * s, r.width - 12 * s, fila), blanco, ScaleMode.StretchToFill,
                                    true, 0f, new Color(0.95f, 0.70f, 0.20f, 0.55f * brillo), 0f, 0f);
            }
            var estilo = t.origen == actor.Estado ? activa : inactiva;
            GUI.Label(new Rect(x, yi, 120 * s, fila), t.origen, estilo);
            GUI.Label(new Rect(x + 120 * s, yi, 150 * s, fila), t.evento, estilo);
            GUI.Label(new Rect(x + 275 * s, yi, 120 * s, fila), string.IsNullOrEmpty(t.guarda) ? "" : "si " + t.guarda, estilo);
            GUI.Label(new Rect(x + 400 * s, yi, 180 * s, fila), "→  " + t.destino, estilo);
        }
    }

    void Banner(float s)
    {
        bool gano = Slime.EnEstadoFinal;
        var r = new Rect(Screen.width / 2f - 320 * s, 146 * s, 640 * s, 118 * s);
        GUI.Box(r, GUIContent.none, panelOpaco);
        var estilo = new GUIStyle(banner);
        estilo.normal.textColor = gano ? new Color(0.55f, 0.9f, 0.5f) : Naranja;
        GUI.Label(new Rect(r.x, r.y + 12 * s, r.width, 44 * s), gano ? "Victoria" : "Derrota", estilo);
        string detalle = gano ? "El slime llegó a su estado final: " + Slime.Estado
                              : "El caballero llegó a su estado final: " + Caballero.Estado;
        GUI.Label(new Rect(r.x, r.y + 60 * s, r.width, 24 * s), detalle, new GUIStyle(texto) { alignment = TextAnchor.UpperCenter });
        GUI.Label(new Rect(r.x, r.y + 86 * s, r.width, 22 * s), "R: jugar otra vez", new GUIStyle(pequeno) { alignment = TextAnchor.UpperCenter });
    }
}
