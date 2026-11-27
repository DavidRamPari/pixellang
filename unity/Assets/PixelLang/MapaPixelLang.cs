using System;
using UnityEngine;

// Contenido de pixellang.json, el mapa que genera el compilador junto con la biblioteca
// (python src/main.py <programa> --emitir build/pixellang). Para cada personaje guarda los
// nombres de sus estados, eventos y atributos en el orden de sus índices, y para cada bloque
// simular, la traza que dio la máquina de código de tres direcciones.
[Serializable]
public class AtributoPixelLang
{
    public int indice;
    public string nombre;
    public string tipo;
}

[Serializable]
public class PersonajePixelLang
{
    public int indice;
    public string nombre;
    public string[] estados;
    public string[] finales;
    public string[] eventos;
    public AtributoPixelLang[] atributos;
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
    public SimulacionPixelLang[] simulaciones;

    public static MapaPixelLang Cargar()
    {
        var texto = Resources.Load<TextAsset>("pixellang");
        if (texto == null)
            throw new InvalidOperationException("Falta Assets/Resources/pixellang.json");
        return JsonUtility.FromJson<MapaPixelLang>(texto.text);
    }
}
