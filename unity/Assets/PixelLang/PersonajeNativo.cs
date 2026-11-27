using System;
using System.Globalization;

// Un personaje de PixelLang ejecutado por la biblioteca nativa. Traduce los nombres del
// programa a los índices de la interfaz C y compara el resultado con la traza del TAC.
// No contiene reglas del personaje: las transiciones y las acciones están en la biblioteca.
public class PersonajeNativo
{
    public readonly PersonajePixelLang datos;

    public PersonajeNativo(PersonajePixelLang datos)
    {
        this.datos = datos;
    }

    public int Error { get; private set; }

    public int Iniciar()
    {
        return Error = PixelLangNative.pl_iniciar(datos.indice);
    }

    public int Enviar(string evento)
    {
        return Error = PixelLangNative.pl_evento(datos.indice, Array.IndexOf(datos.eventos, evento));
    }

    public string Estado
    {
        get
        {
            int j = PixelLangNative.pl_estado(datos.indice);
            return j >= 0 && j < datos.estados.Length ? datos.estados[j] : "";
        }
    }

    public bool EnEstadoFinal
    {
        get { return Array.IndexOf(datos.finales, Estado) >= 0; }
    }

    public int Atributo(string nombre)
    {
        return Array.FindIndex(datos.atributos, a => a.nombre == nombre);
    }

    public double Valor(int a)
    {
        switch (datos.atributos[a].tipo)
        {
            case "entero": return PixelLangNative.pl_entero(datos.indice, a);
            case "real": return PixelLangNative.pl_real(datos.indice, a);
            default: return PixelLangNative.pl_logico(datos.indice, a);
        }
    }

    // Igual que mostrar() de la máquina de TAC: 100, 2.5, 0.0, verdadero
    public string Texto(int a)
    {
        double v = Valor(a);
        switch (datos.atributos[a].tipo)
        {
            case "entero":
                return ((int)v).ToString(CultureInfo.InvariantCulture);
            case "real":
                string texto = v.ToString("F6", CultureInfo.InvariantCulture).TrimEnd('0');
                return texto.EndsWith(".") ? texto + "0" : texto;
            default:
                return v != 0 ? "verdadero" : "falso";
        }
    }

    // El paso coincide si la biblioteca está en el mismo estado y con los mismos atributos
    // que la máquina de TAC, o si las dos terminaron en un error de ejecución.
    public bool Coincide(PasoPixelLang paso)
    {
        if (string.IsNullOrEmpty(paso.estado))
            return Error != 0;
        if (Error != 0 || Estado != paso.estado || paso.valores.Length != datos.atributos.Length)
            return false;
        for (int a = 0; a < datos.atributos.Length; a++)
        {
            double esperado = paso.valores[a], obtenido = Valor(a);
            if (double.IsNaN(esperado) && double.IsNaN(obtenido))
                continue;
            if (Math.Abs(esperado - obtenido) > 1e-9 * Math.Max(1.0, Math.Abs(esperado)))
                return false;
        }
        return true;
    }
}
