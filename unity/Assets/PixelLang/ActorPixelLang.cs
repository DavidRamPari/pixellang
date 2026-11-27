using System;

// Un personaje de PixelLang dentro del juego. Envía los eventos a la biblioteca y, con la
// función de transición δ que trae el mapa, averigua qué transición tomó la biblioteca, o si
// ignoró el evento porque el estado actual no tiene una transición con ese evento (o ninguna
// de sus guardas se cumple). No decide nada: solo compara el estado antes y después.
public class ActorPixelLang
{
    public readonly PersonajeNativo nativo;

    public ActorPixelLang(PersonajePixelLang datos) : this(datos, datos.indice) { }

    public ActorPixelLang(PersonajePixelLang datos, int instancia)
    {
        nativo = new PersonajeNativo(datos, instancia);
    }

    public PersonajePixelLang Datos { get { return nativo.datos; } }
    public int Instancia { get { return nativo.instancia; } }
    public TransicionPixelLang[] Delta { get { return nativo.datos.transiciones ?? new TransicionPixelLang[0]; } }
    public string Estado { get { return nativo.Estado; } }
    public bool EnEstadoFinal { get { return nativo.EnEstadoFinal; } }

    public int UltimaTransicion { get; private set; } = -1;   // índice en Delta
    public float MomentoTransicion { get; private set; }
    public string Ignorado { get; private set; } = "";
    public float MomentoIgnorado { get; private set; } = -100f;

    public void Iniciar(float ahora)
    {
        nativo.Iniciar();
        UltimaTransicion = -1;
        MomentoTransicion = ahora;
        Ignorado = "";
        MomentoIgnorado = -100f;
    }

    // Devuelve el índice de la transición que tomó la biblioteca, o -1 si no tomó ninguna
    public int Enviar(string evento, float ahora)
    {
        string antes = Estado;
        nativo.Enviar(evento);
        if (nativo.Error != 0)
        {
            Ignorado = evento + ": error de ejecución " + nativo.Error;
            MomentoIgnorado = ahora;
            return -1;
        }
        int tomada = Buscar(antes, evento, Estado);
        if (tomada >= 0)
        {
            UltimaTransicion = tomada;
            MomentoTransicion = ahora;
        }
        else
        {
            bool hayGuardas = Array.Exists(Delta, t => t.origen == antes && t.evento == evento);
            Ignorado = hayGuardas
                ? evento + ": en " + antes + " ninguna guarda se cumple"
                : evento + ": " + antes + " no tiene esa transición";
            MomentoIgnorado = ahora;
        }
        return tomada;
    }

    public int Buscar(string origen, string evento, string destino)
    {
        var delta = Delta;
        for (int i = 0; i < delta.Length; i++)
            if (delta[i].origen == origen && delta[i].evento == evento && delta[i].destino == destino)
                return i;
        return -1;
    }

    public double Valor(string atributo)
    {
        int a = nativo.Atributo(atributo);
        return a >= 0 ? nativo.Valor(a) : 0.0;
    }
}
