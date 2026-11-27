using System;
using UnityEngine;

// Contenido de pixellang.json, el mapa que genera el compilador junto con la biblioteca
// (python src/main.py <programa> --emitir build/unity/pixellang). Para cada personaje guarda
// los nombres de sus estados, eventos y atributos en el orden de sus índices y su función de
// transición δ; también cuántas instancias tiene cada personaje en la biblioteca y, para cada
// bloque simular, la traza que dio la máquina de código de tres direcciones.
[Serializable]
public class AtributoPixelLang
{
    public int indice;
    public string nombre;
    public string tipo;
}

[Serializable]
public class TransicionPixelLang
{
    public string origen;
    public string evento;
    public string guarda;       // vacía si la transición no tiene guarda
    public string destino;
}

[Serializable]
public class PersonajePixelLang
{
    public int indice;
    public string nombre;
    public string[] estados;
    public string inicial;
    public string[] finales;
    public string[] eventos;
    public AtributoPixelLang[] atributos;
    public TransicionPixelLang[] transiciones;
}

[Serializable]
public class PasoPixelLang
{
    public string evento;
    public string estado;       // vacío si en este paso hubo un error de ejecución
    public double[] valores;    // atributos en orden; un lógico vale 1 o 0
    public string error;
}

[Serializable]
public class SimulacionPixelLang
{
    public int personaje;
    public PasoPixelLang[] pasos;
}

[Serializable]
public class MapaPixelLang
{
    public PersonajePixelLang[] personajes;
    public int instancias_por_personaje;
    public SimulacionPixelLang[] simulaciones;

    public static MapaPixelLang Cargar()
    {
        var texto = Resources.Load<TextAsset>("pixellang");
        if (texto == null)
            throw new InvalidOperationException("Falta Assets/Resources/pixellang.json");
        return JsonUtility.FromJson<MapaPixelLang>(texto.text);
    }

    public PersonajePixelLang Personaje(string nombre)
    {
        var personaje = Array.Find(personajes, p => p.nombre == nombre);
        if (personaje == null)
            throw new InvalidOperationException("El programa no tiene el personaje " + nombre);
        return personaje;
    }

    // Número de la instancia n de un personaje en la interfaz C: p + P·n
    public int Instancia(PersonajePixelLang personaje, int n)
    {
        if (n < 0 || n >= instancias_por_personaje)
            throw new ArgumentOutOfRangeException(nameof(n),
                "La biblioteca tiene " + instancias_por_personaje + " instancias por personaje");
        return personaje.indice + personajes.Length * n;
    }
}
