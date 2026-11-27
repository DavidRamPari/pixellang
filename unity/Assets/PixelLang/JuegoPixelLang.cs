using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

// Minijuego de PixelLang: el caballero, que controla el jugador, contra dos slimes. Son los
// personajes de ejemplos/juego.pxl, compilados juntos en pixellang.dll: el caballero es el
// personaje 0 y el slime, el personaje 1. Los dos slimes son dos instancias del mismo
// personaje: siguen la misma función de transición δ, pero cada uno tiene su ficha en la
// biblioteca, con su propio estado y su propia vida. La instancia n del personaje p se elige
// con el número p + 2·n: el caballero es la instancia 0 y los slimes, la 1 y la 3.
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

    // Dónde aparece cada slime, entre qué puntos patrulla y hacia dónde empieza a moverse
    struct Aparicion
    {
        public float x, izquierda, derecha;
        public int direccion;
        public Aparicion(float x, float izquierda, float derecha, int direccion)
        {
            this.x = x;
            this.izquierda = izquierda;
            this.derecha = derecha;
            this.direccion = direccion;
        }
    }

    static readonly Aparicion[] Apariciones =
    {
        new Aparicion(5.5f, 4.0f, 6.5f, 1),
        new Aparicion(7.6f, 4.2f, 7.8f, -1),
    };

    // Ajustes del motor: posiciones, distancias y velocidades del movimiento
    const float XCaballero = -3.2f;
    const float VisionSlime = 7.5f, PerdidaSlime = 11f;
    const float VelocidadPatrulla = 1.0f, VelocidadPersecucion = 1.9f;
    const float Separacion = 1.8f;        // distancia mínima entre dos slimes que persiguen
    const float LimiteDerecho = 7.9f;
    const float Contacto = 1.15f;
    const float AlcanceBase = 1.6f;
    const float AlturaPisoton = 0.6f;
    const float EscalaSalto = 0.9f;       // unidades del mundo por cada unidad del atributo y

    static readonly Color Naranja = new Color(1f, 0.62f, 0.25f);
    static readonly Color Gris = new Color(0.62f, 0.65f, 0.72f);

    // Cuerpo de un slime en la escena: lo que la biblioteca no guarda (la posición, el empuje
    // de un golpe, el sentido de la patrulla y si ve al caballero) y sus dibujos
    class CuerpoSlime
    {
        public ActorPixelLang actor;
        public int numero;                // 1 o 2, como se ve en pantalla
        public float x, empuje, izquierda, derecha;
        public int direccion = 1, mirada = 1;
        public bool ve, quieto;
        public float cierre = -1f, reposo;
        public Transform raiz;
        public SpriteRenderer figura;
        public readonly List<Transform> estrellas = new List<Transform>();
    }

    public ActorPixelLang Caballero { get; private set; }
    public ActorPixelLang[] Slimes { get; private set; } = new ActorPixelLang[0];
    public bool FinDePartida
    {
        get
        {
            return Caballero != null
                   && (Caballero.EnEstadoFinal || Array.TrueForAll(Slimes, s => s.EnEstadoFinal));
        }
    }

    string problema = "";
    float alturaCaballero, finPartida = -1f, cierreCaballero = -1f;
    bool golpeDeEsteAtaque, demostracion;
    Coroutine guion;
    string carpetaCaptura;
    int cuadro;

    Transform caballeroBase;
    SpriteRenderer caballeroFigura, tajo;
    readonly List<Transform> estrellasCaballero = new List<Transform>();
    readonly List<CuerpoSlime> slimes = new List<CuerpoSlime>();

    class Aviso
    {
        public string texto;
        public Vector3 posicion;
        public float inicio;
        public Color color;
        public ActorPixelLang actor;
        public float subida;      // los avisos anteriores suben para dejar lugar al nuevo
    }
    readonly List<Aviso> avisos = new List<Aviso>();

    void Start()
    {
        PrepararEscena();
        try
        {
            var mapa = MapaPixelLang.Cargar();
            var caballero = mapa.Personaje("Caballero");
            var slime = mapa.Personaje("Slime");
            Caballero = new ActorPixelLang(caballero, mapa.Instancia(caballero, 0));
            foreach (var cuerpo in slimes)
                cuerpo.actor = new ActorPixelLang(slime, mapa.Instancia(slime, cuerpo.numero - 1));
            Slimes = slimes.ConvertAll(c => c.actor).ToArray();
            Reiniciar();
        }
        catch (Exception e)
        {
            Caballero = null;
            Slimes = new ActorPixelLang[0];
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
        foreach (var s in slimes)
        {
            var a = Apariciones[s.numero - 1];
            s.actor.Iniciar(Time.time);
            s.x = a.x;
            s.izquierda = a.izquierda;
            s.derecha = a.derecha;
            s.direccion = s.mirada = a.direccion;
            s.empuje = 0f;
            s.ve = s.quieto = false;
            s.cierre = -1f;
        }
        golpeDeEsteAtaque = false;
        alturaCaballero = 0f;
        finPartida = -1f;
        cierreCaballero = -1f;
        avisos.Clear();
    }

    CuerpoSlime Cuerpo(ActorPixelLang actor)
    {
        return slimes.Find(s => s.actor == actor);
    }

    // Eventos ---------------------------------------------------------------------------

    // Todos los eventos pasan por aquí: van a la biblioteca y quedan como aviso en pantalla
    int Enviar(ActorPixelLang actor, string evento, string tecla = null)
    {
        int tomada = actor.Enviar(evento, Time.time);
        Vector3 sobre = actor == Caballero ? caballeroBase.position + new Vector3(0f, 3.15f, 0f)
                                           : Cuerpo(actor).raiz.position + new Vector3(0f, 2.6f, 0f);
        string texto = (tecla != null ? "[" + tecla + "] " : "") + evento + (tomada < 0 ? ": ignorado" : "");
        foreach (var anterior in avisos)
            if (anterior.actor == actor)
                anterior.subida += 20f;
        avisos.Add(new Aviso
        {
            texto = texto, posicion = sobre, inicio = Time.time, color = tomada < 0 ? Naranja : Color.white,
            actor = actor,
        });
        if (actor == Caballero && tomada >= 0 && Caballero.Delta[tomada].destino == "Atacando")
            golpeDeEsteAtaque = false;     // cada ataque puede golpear una vez
        return tomada;
    }

    // Lo que hace una tecla: enviar un evento al caballero
    public void Pulsar(string evento, string tecla)
    {
        if (Caballero != null && !FinDePartida)
            Enviar(Caballero, evento, tecla);
    }

    static float Distancia(CuerpoSlime s) { return s.x - XCaballero; }

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
            {
                if (demostracion)
                    IniciarDemostracion();
                else
                    Reiniciar();
            }
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
            MoverSlimes(Time.deltaTime);
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
        foreach (var s in slimes)
            if (AnimacionesSlime.TryGetValue(s.actor.Estado, out a)
                && Time.time - s.actor.MomentoTransicion >= a.duracion && s.cierre != s.actor.MomentoTransicion)
            {
                s.cierre = s.actor.MomentoTransicion;
                Enviar(s.actor, a.evento);
            }
    }

    void MoverSlimes(float dt)
    {
        foreach (var s in slimes)
        {
            if (s.actor.EnEstadoFinal)
                continue;                  // aplastado: ya no se mueve ni recibe eventos
            // empuje de un golpe
            s.x += s.empuje * dt;
            s.empuje = Mathf.MoveTowards(s.empuje, 0f, 12f * dt);
            // Percepción: el juego avisa cuando el slime empieza a ver al caballero o lo pierde
            bool ve = s.ve ? Distancia(s) <= PerdidaSlime : Distancia(s) <= VisionSlime;
            if (ve != s.ve)
            {
                s.ve = ve;
                Enviar(s.actor, ve ? "ver_jugador" : "perder_jugador");
            }
            // Cómo se mueve en cada estado (el estado lo decide la biblioteca)
            string estado = s.actor.Estado;
            if (estado == "Patrulla")
            {
                s.x += s.direccion * VelocidadPatrulla * dt;
                if (s.x < s.izquierda) s.direccion = 1;
                if (s.x > s.derecha) s.direccion = -1;
            }
            else if (estado == "Persecucion" && s.empuje < 0.01f)
            {
                s.x -= VelocidadPersecucion * dt;
                // no se encima al slime que va delante
                float delante = float.MinValue;
                foreach (var otro in slimes)
                    if (otro != s && !otro.actor.EnEstadoFinal && otro.x < s.x)
                        delante = Mathf.Max(delante, otro.x);
                if (delante > float.MinValue)
                    s.x = Mathf.Max(s.x, delante + Separacion);
            }
            s.x = Mathf.Clamp(s.x, XCaballero + 0.6f, LimiteDerecho);
        }
    }

    void Contactos()
    {
        // La espada alcanza al slime más cercano; cada ataque golpea una sola vez
        if (Caballero.Estado == "Atacando" && !golpeDeEsteAtaque)
        {
            CuerpoSlime blanco = null;
            foreach (var s in slimes)
                if (!s.actor.EnEstadoFinal && Distancia(s) <= Alcance()
                    && (blanco == null || Distancia(s) < Distancia(blanco)))
                    blanco = s;
            if (blanco != null)
            {
                golpeDeEsteAtaque = true;
                Enviar(blanco.actor, "recibir_golpe");
                blanco.empuje = 7f;
            }
        }
        foreach (var s in slimes)
        {
            if (s.actor.EnEstadoFinal || Distancia(s) > Contacto || s.empuje > 0.5f)
                continue;
            if (alturaCaballero >= AlturaPisoton)
            {
                // el caballero cae sobre el slime
                Enviar(s.actor, "recibir_golpe");
                s.empuje = 7f;
            }
            else
            {
                Enviar(Caballero, "recibir_golpe");
                s.empuje = 6f;             // el slime rebota
            }
        }
    }

    // Guion de la partida de demostración: solo pulsa teclas, como lo haría un jugador
    public void IniciarDemostracion()
    {
        if (guion != null)
            StopCoroutine(guion);
        demostracion = true;
        Reiniciar();
        guion = StartCoroutine(Demostracion());
    }

    // Distancia al slime más cercano que persigue al caballero, sin contar uno que va empujado
    float Cercano()
    {
        float d = float.MaxValue;
        foreach (var s in slimes)
            if (s.actor.Estado == "Persecucion" && s.empuje < 0.5f)
                d = Mathf.Min(d, Distancia(s));
        return d;
    }

    IEnumerator Demostracion()
    {
        // 1. Ataca cuando el primer slime está cerca (con velocidad 1.5, la espada llega a 2.5)
        yield return new WaitUntil(() => Caballero.Estado == "Reposo" && Cercano() <= 2.4f);
        Pulsar("atacar", "J");
        // 2. Deja que un slime lo toque y, aturdido, intenta atacar: la biblioteca lo ignora
        yield return new WaitUntil(() => Caballero.Estado == "Aturdido");
        yield return new WaitForSeconds(0.35f);
        Pulsar("atacar", "J");
        // 3. Salta y cae sobre el slime
        yield return new WaitUntil(() => Caballero.Estado == "Reposo" && Cercano() <= 2.1f);
        Pulsar("saltar", "Espacio");
        // 4. Ataca cada vez que un slime se acerca: con vida 0, la guarda lleva a cada uno a
        //    su estado final
        while (!FinDePartida)
        {
            yield return new WaitUntil(() => FinDePartida || (Caballero.Estado == "Reposo" && Cercano() <= 2.4f));
            if (!FinDePartida)
                Pulsar("atacar", "J");
            yield return null;
        }
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
        camara.transform.position = new Vector3(0.5f, 1.64f, -10f);
        camara.clearFlags = CameraClearFlags.SolidColor;
        camara.backgroundColor = new Color(0.10f, 0.12f, 0.19f);

        var azar = new System.Random(5);
        var punto = DibujosPixelLang.DeColor(new Color(0.85f, 0.88f, 1f, 0.7f));
        for (int i = 0; i < 28; i++)
            Figura("Estrella del cielo", punto, new Vector3((float)azar.NextDouble() * 18f - 8.5f,
                   2.5f + (float)azar.NextDouble() * 1.9f, 0f), Vector3.one * 0.06f, -5);
        Figura("Colinas lejanas", DibujosPixelLang.Colinas(new Color(0.14f, 0.17f, 0.26f), 7),
               new Vector3(0f, -0.3f, 0f), Vector3.one, -4);
        Figura("Colinas", DibujosPixelLang.Colinas(new Color(0.17f, 0.22f, 0.30f), 41),
               new Vector3(2f, -0.6f, 0f), new Vector3(1f, 0.6f, 1f), -3);
        Figura("Suelo", DibujosPixelLang.DeColor(new Color(0.27f, 0.21f, 0.16f)),
               new Vector3(0f, -2.5f, 0f), new Vector3(40f, 5f, 1f), 0);
        Figura("Pasto", DibujosPixelLang.DeColor(new Color(0.30f, 0.56f, 0.28f)),
               new Vector3(0f, -0.1f, 0f), new Vector3(40f, 0.2f, 1f), 1);

        var estrella = DibujosPixelLang.Estrella();
        caballeroBase = new GameObject("Caballero").transform;
        caballeroFigura = Figura("Dibujo", DibujosPixelLang.Caballero(), Vector3.zero, Vector3.one, 3, caballeroBase);
        tajo = Figura("Tajo", DibujosPixelLang.Tajo(), new Vector3(0.95f, 1.0f, 0f), Vector3.one, 4, caballeroBase);
        for (int i = 0; i < 3; i++)
            estrellasCaballero.Add(Figura("Estrella", estrella, Vector3.zero, Vector3.one, 5).transform);

        var dibujoSlime = DibujosPixelLang.Slime();
        for (int n = 0; n < Apariciones.Length; n++)
        {
            var cuerpo = new CuerpoSlime { numero = n + 1 };
            cuerpo.raiz = new GameObject("Slime " + cuerpo.numero).transform;
            cuerpo.figura = Figura("Dibujo", dibujoSlime, Vector3.zero, Vector3.one, 3, cuerpo.raiz);
            for (int i = 0; i < 3; i++)
                cuerpo.estrellas.Add(Figura("Estrella", estrella, Vector3.zero, Vector3.one, 5).transform);
            slimes.Add(cuerpo);
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

        // Slimes: rebotan al moverse (cada uno con su ritmo), miran hacia donde van, se
        // aplastan con un golpe y quedan planos en su estado final
        foreach (var c in slimes)
        {
            Acomodar(c, dt);
            string estado = c.actor.Estado;
            float salto = 0f, escalaY;
            if (estado == "Patrulla" || estado == "Persecucion")
            {
                float fase = ahora * (estado == "Persecucion" ? 7f : 4.5f) + c.numero * 1.3f;
                salto = Mathf.Abs(Mathf.Sin(fase)) * 0.35f;
                escalaY = 1f + 0.08f * Mathf.Cos(2f * fase);
                c.mirada = estado == "Persecucion" ? -1 : c.direccion;
            }
            else
                escalaY = c.actor.EnEstadoFinal ? 0.3f : 0.65f;
            c.raiz.position = new Vector3(c.x, salto, 0f);
            c.figura.transform.localScale = new Vector3(1f + 0.5f * (1f - escalaY), escalaY, 1f);
            c.figura.flipX = c.mirada < 0;
            c.figura.sortingOrder = c.actor.EnEstadoFinal ? 2 : 3;     // el que sigue vivo pasa por encima
            c.figura.color = c.actor.EnEstadoFinal ? new Color(0.5f, 0.55f, 0.5f)
                           : estado == "Persecucion" ? new Color(1f, 0.82f, 0.82f) : Color.white;
            Estrellas(c.estrellas, c.raiz.position + new Vector3(0f, 1.25f, 0f), estado == "Aturdido");
        }
    }

    // Un slime que llega a su estado final se acomoda al lado de los que ya estaban aplastados,
    // para que no queden uno encima del otro
    void Acomodar(CuerpoSlime c, float dt)
    {
        const float Ancho = 1.7f;
        if (c.actor.EnEstadoFinal && !c.quieto)
        {
            c.quieto = true;
            c.reposo = c.x;
            for (int intento = 0; intento < 10; intento++)
            {
                bool movido = false;
                foreach (var otro in slimes)
                    if (otro != c && otro.quieto && Mathf.Abs(otro.reposo - c.reposo) < Ancho)
                    {
                        float nuevo = otro.reposo + (c.reposo >= otro.reposo ? Ancho : -Ancho);
                        c.reposo = nuevo < XCaballero + 2f ? otro.reposo + Ancho : nuevo;
                        movido = true;
                    }
                if (!movido)
                    break;
            }
            c.reposo = Mathf.Min(c.reposo, LimiteDerecho);
        }
        if (c.quieto)
            c.x = Mathf.MoveTowards(c.x, c.reposo, 4f * dt);
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

    GUIStyle titulo, subtitulo, nombre, estadoGrande, estadoFila, texto, pequeno, pequenoDerecha, celda, aviso,
             etiqueta, etiquetaPequena, banner, panel, panelOpaco;
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
        estadoFila = Crear(19, FontStyle.Bold, TextAnchor.UpperLeft);
        texto = Crear(15, FontStyle.Normal, TextAnchor.UpperLeft);
        pequeno = Crear(13, FontStyle.Normal, TextAnchor.UpperLeft);
        pequeno.normal.textColor = Gris;
        pequenoDerecha = Crear(13, FontStyle.Normal, TextAnchor.UpperRight);
        pequenoDerecha.normal.textColor = Gris;
        celda = Crear(13, FontStyle.Normal, TextAnchor.UpperLeft);
        aviso = Crear(15, FontStyle.Bold, TextAnchor.MiddleCenter);
        etiqueta = Crear(17, FontStyle.Bold, TextAnchor.MiddleCenter);
        etiquetaPequena = Crear(13, FontStyle.Normal, TextAnchor.MiddleCenter);
        etiquetaPequena.normal.textColor = Gris;
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
        TarjetaSlimes(new Rect(Screen.width - 430 * s, 16 * s, 410 * s, 108 * s), 30, s);
        float cx = Screen.width / 2f;
        GUI.Label(new Rect(cx - 210 * s, 20 * s, 420 * s, 30 * s), "PixelLang en Unity", titulo);
        GUI.Label(new Rect(cx - 210 * s, 52 * s, 420 * s, 22 * s), "El juego envía los eventos; pixellang.dll decide el estado", subtitulo);
        GUI.Label(new Rect(cx - 210 * s, 78 * s, 420 * s, 22 * s),
                  demostracion ? "Partida de demostración: un guion pulsa las teclas"
                               : "Espacio: saltar     J: atacar     R: reiniciar     Tab: validación",
                  new GUIStyle(pequeno) { alignment = TextAnchor.UpperCenter });

        Etiqueta(caballeroBase.position + new Vector3(0f, 2.6f, 0f), Caballero.Estado, etiqueta, Color.white, s);
        foreach (var c in slimes)
        {
            // La etiqueta no rebota con el slime. La de uno aplastado queda abajo, junto a él, y
            // se desvanece cuando otro slime pasa por encima
            bool final = c.actor.EnEstadoFinal;
            float alfa = 1f;
            if (final)
                foreach (var otro in slimes)
                    if (!otro.actor.EnEstadoFinal)
                        alfa = Mathf.Min(alfa, Mathf.Clamp01((Mathf.Abs(otro.x - c.x) - 0.9f) / 0.7f));
            float alto = final ? 0.95f : 1.95f;
            var color = final ? Gris : Color.white;
            color.a = alfa;
            var gris = Gris;
            gris.a = alfa;
            Etiqueta(new Vector3(c.x, alto, 0f), c.actor.Estado, etiqueta, color, s);
            Etiqueta(new Vector3(c.x, alto + 0.3f, 0f), "slime " + c.numero, etiquetaPequena, gris, s);
        }
        Avisos(s);

        TablaDelta(new Rect(20 * s, 524 * s, 610 * s, 186 * s), "δ del caballero (personaje 0)", new[] { Caballero }, s);
        TablaDelta(new Rect(Screen.width - 630 * s, 524 * s, 610 * s, 186 * s), "δ del slime (personaje 1)", Slimes, s);
        if (FinDePartida)
            Banner(s);
    }

    void Barra(Rect barra, float parte)
    {
        parte = Mathf.Clamp01(parte);
        GUI.DrawTexture(barra, blanco, ScaleMode.StretchToFill, false, 0f, new Color(0.22f, 0.24f, 0.30f), 0f, 0f);
        var color = parte > 0.5f ? new Color(0.36f, 0.78f, 0.38f) : parte > 0.25f ? new Color(0.95f, 0.75f, 0.25f) : new Color(0.9f, 0.3f, 0.3f);
        GUI.DrawTexture(new Rect(barra.x, barra.y, barra.width * parte, barra.height), blanco, ScaleMode.StretchToFill, false, 0f, color, 0f, 0f);
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
        Barra(barra, vida / (float)vidaMaxima);
        GUI.Label(new Rect(barra.xMax + 12 * s, y + 60 * s, 150 * s, 22 * s), "vida " + vida, texto);
        string otros = "";
        for (int a = 0; a < actor.Datos.atributos.Length; a++)
            if (actor.Datos.atributos[a].nombre != "vida")
                otros += actor.Datos.atributos[a].nombre + " " + actor.nativo.Texto(a) + "     ";
        GUI.Label(new Rect(x, y + 82 * s, r.width - 32 * s, 20 * s), otros.TrimEnd(), pequeno);
    }

    // Una fila por slime: los dos son instancias del mismo personaje, cada una con su ficha
    void TarjetaSlimes(Rect r, int vidaMaxima, float s)
    {
        GUI.Box(r, GUIContent.none, panel);
        float x = r.x + 16 * s, y = r.y + 10 * s;
        GUI.Label(new Rect(x, y, 200 * s, 24 * s), "Slimes", nombre);
        GUI.Label(new Rect(r.xMax - 216 * s, y + 3 * s, 200 * s, 20 * s), "estado y atributos de la DLL", pequenoDerecha);
        string instancias = "";
        foreach (var c in slimes)
        {
            float yc = y + 27 * s + (c.numero - 1) * 27 * s;
            GUI.Label(new Rect(x, yc + 3 * s, 80 * s, 22 * s), "Slime " + c.numero, texto);
            var estilo = new GUIStyle(estadoFila);
            estilo.normal.textColor = c.actor.EnEstadoFinal ? Naranja : Color.white;
            GUI.Label(new Rect(x + 72 * s, yc, 150 * s, 26 * s), c.actor.Estado, estilo);
            int vida = (int)c.actor.Valor("vida");
            var barra = new Rect(x + 214 * s, yc + 9 * s, 92 * s, 10 * s);
            Barra(barra, vida / (float)vidaMaxima);
            GUI.Label(new Rect(barra.xMax + 10 * s, yc + 3 * s, 80 * s, 22 * s), "vida " + vida, texto);
            instancias += (instancias == "" ? "" : c.numero == slimes.Count ? " y " : ", ") + c.actor.Instancia;
        }
        GUI.Label(new Rect(x, y + 82 * s, r.width - 32 * s, 20 * s),
                  "la misma δ, una ficha para cada uno: instancias " + instancias, pequeno);
    }

    void Etiqueta(Vector3 mundo, string contenido, GUIStyle estilo, Color color, float s)
    {
        if (color.a <= 0f)
            return;
        var p = Camera.main.WorldToScreenPoint(mundo);
        var conColor = new GUIStyle(estilo);
        conColor.normal.textColor = color;
        // en lo alto del salto, la etiqueta del caballero no tapa su tarjeta
        float y = Mathf.Max(Screen.height - p.y - 14 * s, 130 * s);
        GUI.Label(new Rect(p.x - 120 * s, y, 240 * s, 28 * s), contenido, conColor);
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

    // La δ de un personaje. Si varias instancias la usan (los slimes), se ilumina la última
    // transición que tomó cualquiera de ellas y se dice cuál fue
    void TablaDelta(Rect r, string tituloTabla, ActorPixelLang[] actores, float s)
    {
        GUI.Box(r, GUIContent.none, panel);
        float x = r.x + 14 * s, y = r.y + 8 * s;
        GUI.Label(new Rect(x, y, 320 * s, 22 * s), tituloTabla, new GUIStyle(nombre) { fontSize = Mathf.RoundToInt(15 * s) });
        bool varios = actores.Length > 1;
        int ignoro = 0, tomo = -1;
        for (int k = 0; k < actores.Length; k++)
        {
            if (actores[k].MomentoIgnorado > actores[ignoro].MomentoIgnorado)
                ignoro = k;
            if (actores[k].UltimaTransicion >= 0
                && (tomo < 0 || actores[k].MomentoTransicion > actores[tomo].MomentoTransicion))
                tomo = k;
        }
        float edadIgnorado = Time.time - actores[ignoro].MomentoIgnorado;
        if (edadIgnorado < 2.2f)
        {
            var estilo = new GUIStyle(pequenoDerecha) { fontStyle = FontStyle.Bold };
            estilo.normal.textColor = new Color(Naranja.r, Naranja.g, Naranja.b, Mathf.Clamp01((2.2f - edadIgnorado) / 0.6f));
            GUI.Label(new Rect(r.xMax - 334 * s, y + 2 * s, 320 * s, 20 * s),
                      (varios ? "slime " + (ignoro + 1) + ", " : "") + actores[ignoro].Ignorado, estilo);
        }
        y += 27 * s;
        float fila = 14.6f * s;
        var delta = actores[0].Delta;
        var activa = new GUIStyle(celda);
        var inactiva = new GUIStyle(celda);
        inactiva.normal.textColor = new Color(0.45f, 0.48f, 0.55f);
        for (int i = 0; i < delta.Length; i++)
        {
            var t = delta[i];
            float yi = y + i * fila;
            if (tomo >= 0 && i == actores[tomo].UltimaTransicion)
            {
                float brillo = Mathf.Clamp01(1.8f - (Time.time - actores[tomo].MomentoTransicion));
                if (brillo > 0f)
                {
                    GUI.DrawTexture(new Rect(r.x + 6 * s, yi - 1 * s, r.width - 12 * s, fila), blanco, ScaleMode.StretchToFill,
                                    true, 0f, new Color(0.95f, 0.70f, 0.20f, 0.55f * brillo), 0f, 0f);
                    if (varios)
                    {
                        var quien = new GUIStyle(pequenoDerecha) { fontStyle = FontStyle.Bold };
                        quien.normal.textColor = new Color(1f, 1f, 1f, brillo);
                        GUI.Label(new Rect(r.xMax - 104 * s, yi - 1 * s, 90 * s, fila), "slime " + (tomo + 1), quien);
                    }
                }
            }
            var estiloFila = Array.Exists(actores, a => a.Estado == t.origen) ? activa : inactiva;
            GUI.Label(new Rect(x, yi, 120 * s, fila), t.origen, estiloFila);
            GUI.Label(new Rect(x + 120 * s, yi, 150 * s, fila), t.evento, estiloFila);
            GUI.Label(new Rect(x + 275 * s, yi, 120 * s, fila), string.IsNullOrEmpty(t.guarda) ? "" : "si " + t.guarda, estiloFila);
            GUI.Label(new Rect(x + 400 * s, yi, 180 * s, fila), "→  " + t.destino, estiloFila);
        }
    }

    void Banner(float s)
    {
        bool gano = Array.TrueForAll(Slimes, a => a.EnEstadoFinal);
        var r = new Rect(Screen.width / 2f - 320 * s, 146 * s, 640 * s, 118 * s);
        GUI.Box(r, GUIContent.none, panelOpaco);
        var estilo = new GUIStyle(banner);
        estilo.normal.textColor = gano ? new Color(0.55f, 0.9f, 0.5f) : Naranja;
        GUI.Label(new Rect(r.x, r.y + 12 * s, r.width, 44 * s), gano ? "Victoria" : "Derrota", estilo);
        string quienes = Slimes.Length == 1 ? "El slime llegó" : Slimes.Length == 2 ? "Los dos slimes llegaron"
                       : "Los " + Slimes.Length + " slimes llegaron";
        string detalle = gano ? quienes + " a su estado final: " + Slimes[0].Estado
                              : "El caballero llegó a su estado final: " + Caballero.Estado;
        GUI.Label(new Rect(r.x, r.y + 60 * s, r.width, 24 * s), detalle, new GUIStyle(texto) { alignment = TextAnchor.UpperCenter });
        GUI.Label(new Rect(r.x, r.y + 86 * s, r.width, 22 * s), "R: jugar otra vez", new GUIStyle(pequeno) { alignment = TextAnchor.UpperCenter });
    }
}
