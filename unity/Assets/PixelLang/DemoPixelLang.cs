using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

// Escena de validación del caballero de ejemplos/juego.pxl. Este script no tiene reglas
// propias: envía los eventos a la biblioteca que generó el compilador de PixelLang (pl_evento)
// y dibuja el estado y los atributos que ella devuelve. El botón "Ejecutar la simulación"
// repite el bloque simular del programa y compara cada paso con la traza de la máquina de TAC
// guardada en pixellang.json (nivel 9 del plan de validación). Con Tab se vuelve al minijuego.
//
// Con el argumento -captura <carpeta>, el reproductor ejecuta la simulación sola, guarda un
// cuadro por cada 1/30 de segundo en esa carpeta y se cierra (para grabar el video).
public class DemoPixelLang : MonoBehaviour
{
    public float pausa = 1.2f;   // segundos entre un evento y el siguiente

    static readonly Color[] Tintes =
    {
        Color.white, new Color(0.75f, 0.92f, 1f), new Color(1f, 0.72f, 0.62f),
        new Color(1f, 0.96f, 0.55f), new Color(0.55f, 0.55f, 0.55f), new Color(0.8f, 1f, 0.8f),
    };

    static readonly string[] Errores =
        { "", "división entre cero", "desbordamiento de entero", "índice inválido" };

    MapaPixelLang mapa;
    PersonajeNativo personaje;
    SimulacionPixelLang simulacion;
    readonly List<string> observados = new List<string>();
    readonly List<bool> coincidencias = new List<bool>();
    SpriteRenderer figura;
    Transform figuraBase;
    int atributoAltura = -1;
    string mensaje = "";
    string problema = "";
    bool ejecutando;
    string carpetaCaptura;
    int cuadro;

    GUIStyle titulo, subtitulo, texto, grande, celda, celdaDerecha, boton, panel;
    Texture2D fondoPanel;

    public bool Terminado { get; private set; }
    public int Coincidencias { get; private set; }
    public int TotalPasos { get { return simulacion == null ? 0 : simulacion.pasos.Length; } }
    public PersonajeNativo Personaje { get { return personaje; } }
    public string EstadoMostrado { get; private set; }

    void Start()
    {
        try
        {
            mapa = MapaPixelLang.Cargar();
            simulacion = mapa.simulaciones.Length > 0 ? mapa.simulaciones[0] : null;
            personaje = new PersonajeNativo(mapa.personajes[simulacion != null ? simulacion.personaje : 0]);
            atributoAltura = personaje.Atributo("y");
            personaje.Iniciar();
            mensaje = "Envía eventos con los botones o ejecuta el bloque simular del programa.";
        }
        catch (Exception e)
        {
            personaje = null;
            problema = "No se pudo usar la biblioteca pixellang: " + e.Message;
            Debug.LogError(problema);
        }
        PrepararEscena();
        string[] args = Environment.GetCommandLineArgs();
        int k = Array.IndexOf(args, "-captura");
        if (k >= 0 && k + 1 < args.Length && problema == "")
        {
            carpetaCaptura = args[k + 1];
            Directory.CreateDirectory(carpetaCaptura);
            Time.captureFramerate = 30;
            StartCoroutine(Capturar());
        }
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
        camara.orthographicSize = 4f;
        // el personaje queda centrado en el espacio libre entre los dos paneles
        camara.transform.position = new Vector3(0.75f, 0.6f, -10f);
        camara.clearFlags = CameraClearFlags.SolidColor;
        camara.backgroundColor = new Color(0.11f, 0.13f, 0.19f);

        var suelo = new GameObject("Suelo").AddComponent<SpriteRenderer>();
        suelo.sprite = DibujosPixelLang.DeColor(new Color(0.25f, 0.33f, 0.24f));
        suelo.transform.position = new Vector3(0f, -3f, 0f);
        suelo.transform.localScale = new Vector3(40f, 2f, 1f);

        figuraBase = new GameObject("Caballero").transform;
        figura = new GameObject("Dibujo").AddComponent<SpriteRenderer>();
        figura.transform.SetParent(figuraBase, false);
        figura.sprite = DibujosPixelLang.Caballero();
        figura.sortingOrder = 1;
    }

    void Update()
    {
        var teclado = Keyboard.current;
        if (teclado != null && teclado.tabKey.wasPressedThisFrame && !ejecutando)
        {
            SceneManager.LoadScene("JuegoPixelLang");
            return;
        }
        if (personaje == null || figura == null)
            return;
        // Todo lo que se dibuja sale de la biblioteca: estado, altura y error
        EstadoMostrado = personaje.Estado;
        int j = Array.IndexOf(personaje.datos.estados, EstadoMostrado);
        figura.color = j >= 0 ? Tintes[j % Tintes.Length] : Color.white;
        float altura = atributoAltura >= 0 ? (float)personaje.Valor(atributoAltura) : 0f;
        figuraBase.position = new Vector3(0f, -2f + altura, 0f);
        bool caido = personaje.EnEstadoFinal;
        figura.transform.localRotation = Quaternion.Euler(0f, 0f, caido ? 90f : 0f);
        figura.transform.localPosition = caido ? new Vector3(1f, 0.75f, 0f) : Vector3.zero;
    }

    public void Reiniciar()
    {
        if (personaje == null || ejecutando)
            return;
        personaje.Iniciar();
        observados.Clear();
        coincidencias.Clear();
        Terminado = false;
        mensaje = "Personaje iniciado en " + personaje.Estado + ".";
    }

    public void EjecutarSimulacion()
    {
        if (personaje != null && simulacion != null && !ejecutando)
            StartCoroutine(Simular());
    }

    IEnumerator Simular()
    {
        ejecutando = true;
        Terminado = false;
        Coincidencias = 0;
        observados.Clear();
        coincidencias.Clear();
        for (int i = 0; i < simulacion.pasos.Length; i++)
        {
            var paso = simulacion.pasos[i];
            if (i == 0)
                personaje.Iniciar();
            else
                personaje.Enviar(paso.evento);
            bool coincide = personaje.Coincide(paso);
            observados.Add(personaje.Error != 0 ? "error" : personaje.Estado);
            coincidencias.Add(coincide);
            if (coincide)
                Coincidencias++;
            mensaje = i == 0 ? "inicio" : "evento " + paso.evento;
            yield return new WaitForSeconds(pausa);
        }
        ejecutando = false;
        Terminado = true;
        mensaje = Coincidencias + " de " + TotalPasos + " pasos coinciden con la simulación del TAC.";
    }

    IEnumerator Capturar()
    {
        yield return new WaitForSeconds(1.5f);
        EjecutarSimulacion();
        float fin = -1f;
        while (true)
        {
            yield return new WaitForEndOfFrame();
            var imagen = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(carpetaCaptura, $"cuadro_{cuadro++:D5}.png"), imagen.EncodeToPNG());
            Destroy(imagen);
            if (Terminado && fin < 0f)
                fin = Time.time + 3f;
            if (fin > 0f && Time.time >= fin)
                break;
        }
        Application.Quit();
    }

    // Interfaz ------------------------------------------------------------------------

    void Estilos()
    {
        if (titulo != null)
            return;
        float s = Screen.height / 720f;
        fondoPanel = new Texture2D(1, 1);
        fondoPanel.SetPixel(0, 0, new Color(0.04f, 0.05f, 0.08f, 0.82f));
        fondoPanel.Apply();
        panel = new GUIStyle { normal = { background = fondoPanel } };
        titulo = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(26 * s), fontStyle = FontStyle.Bold };
        subtitulo = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(15 * s) };
        texto = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(18 * s) };
        grande = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(30 * s), fontStyle = FontStyle.Bold };
        celda = new GUIStyle(GUI.skin.label) { fontSize = Mathf.RoundToInt(15 * s), wordWrap = false };
        celdaDerecha = new GUIStyle(celda) { alignment = TextAnchor.UpperRight };
        boton = new GUIStyle(GUI.skin.button) { fontSize = Mathf.RoundToInt(16 * s) };
        foreach (var estilo in new[] { titulo, subtitulo, texto, grande, celda, celdaDerecha })
            estilo.normal.textColor = Color.white;
        subtitulo.normal.textColor = new Color(0.75f, 0.8f, 0.88f);
    }

    void OnGUI()
    {
        Estilos();
        float s = Screen.height / 720f;
        if (problema != "")
        {
            GUI.Label(new Rect(30 * s, 30 * s, Screen.width - 60 * s, 200 * s), problema, texto);
            return;
        }
        if (personaje == null)
            return;
        PanelIzquierdo(s);
        PanelDerecho(s);
        // Nombre del estado sobre el personaje
        var pantalla = Camera.main.WorldToScreenPoint(figuraBase.position + new Vector3(0f, 2.6f, 0f));
        GUI.Label(new Rect(pantalla.x - 150 * s, Screen.height - pantalla.y - 20 * s, 300 * s, 40 * s),
                  EstadoMostrado, new GUIStyle(grande) { alignment = TextAnchor.MiddleCenter });
        GUI.Label(new Rect(370 * s, Screen.height - 60 * s, Screen.width - 870 * s, 50 * s), mensaje,
                  new GUIStyle(texto) { alignment = TextAnchor.MiddleCenter, wordWrap = true });
        GUI.Label(new Rect(370 * s, 22 * s, Screen.width - 870 * s, 24 * s), "Tab: volver al minijuego",
                  new GUIStyle(subtitulo) { alignment = TextAnchor.MiddleCenter });
    }

    void PanelIzquierdo(float s)
    {
        var area = new Rect(20 * s, 20 * s, 340 * s, Screen.height - 40 * s);
        GUI.Box(area, GUIContent.none, panel);
        GUILayout.BeginArea(new Rect(area.x + 18 * s, area.y + 14 * s, area.width - 36 * s, area.height - 28 * s));
        GUILayout.Label("PixelLang en Unity", titulo);
        GUILayout.Label(personaje.datos.nombre + ": lógica compilada en pixellang.dll", subtitulo);
        GUILayout.Space(14 * s);
        GUILayout.Label("Estado", subtitulo);
        GUILayout.Label(EstadoMostrado, grande);
        GUILayout.Space(6 * s);
        for (int a = 0; a < personaje.datos.atributos.Length; a++)
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label(personaje.datos.atributos[a].nombre, texto, GUILayout.Width(160 * s));
            GUILayout.Label(personaje.Texto(a), texto);
            GUILayout.EndHorizontal();
        }
        if (personaje.Error != 0)
            GUILayout.Label("Error de ejecución: " + Errores[Mathf.Clamp(personaje.Error, 0, 3)], texto);
        GUILayout.Space(14 * s);
        GUILayout.Label("Eventos", subtitulo);
        GUI.enabled = !ejecutando;
        foreach (var evento in personaje.datos.eventos)
            if (GUILayout.Button(evento, boton, GUILayout.Height(30 * s)))
            {
                personaje.Enviar(evento);
                mensaje = "evento " + evento + (personaje.Error != 0 ? ": error de ejecución" : "");
            }
        GUILayout.Space(10 * s);
        if (GUILayout.Button("Reiniciar", boton, GUILayout.Height(30 * s)))
            Reiniciar();
        if (GUILayout.Button("Ejecutar la simulación", boton, GUILayout.Height(34 * s)))
            EjecutarSimulacion();
        GUI.enabled = true;
        GUILayout.EndArea();
    }

    void PanelDerecho(float s)
    {
        if (simulacion == null)
            return;
        var area = new Rect(Screen.width - 490 * s, 20 * s, 470 * s, Screen.height - 40 * s);
        GUI.Box(area, GUIContent.none, panel);
        GUILayout.BeginArea(new Rect(area.x + 16 * s, area.y + 14 * s, area.width - 32 * s, area.height - 28 * s));
        GUILayout.Label("Bloque simular", titulo);
        GUILayout.Label("Estado esperado (máquina de TAC) y estado en Unity", subtitulo);
        GUILayout.Space(10 * s);
        Fila(s, "#", "evento", "TAC", "Unity", "");
        for (int i = 0; i < simulacion.pasos.Length; i++)
        {
            var paso = simulacion.pasos[i];
            string esperado = string.IsNullOrEmpty(paso.estado) ? "error" : paso.estado;
            string observado = i < observados.Count ? observados[i] : "";
            string resultado = i < coincidencias.Count ? (coincidencias[i] ? "coincide" : "difiere") : "";
            Fila(s, i.ToString(), paso.evento, esperado, observado, resultado);
        }
        GUILayout.EndArea();
    }

    void Fila(float s, string n, string evento, string esperado, string observado, string resultado)
    {
        GUILayout.BeginHorizontal();
        GUILayout.Label(n, celdaDerecha, GUILayout.Width(24 * s));
        GUILayout.Space(6 * s);
        GUILayout.Label(evento, celda, GUILayout.Width(128 * s));
        GUILayout.Label(esperado, celda, GUILayout.Width(84 * s));
        GUILayout.Label(observado, celda, GUILayout.Width(84 * s));
        GUILayout.Label(resultado, celda);
        GUILayout.EndHorizontal();
    }
}
