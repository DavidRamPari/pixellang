using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;

// Prueba de la biblioteca nativa desde C#, fuera de Unity. Usa las mismas declaraciones
// DllImport que el proyecto de Unity (PixelLangNative.cs) y compara cada paso del bloque
// simular con la traza de la máquina de TAC que guarda pixellang.json.
// Uso: python src/main.py ejemplos/caballero.pxl --emitir build/pixellang --biblioteca
//      dotnet run --project pruebas/nativo
public static class PruebaNativa
{
    public static int Main()
    {
        string ruta = Path.Combine(AppContext.BaseDirectory, "pixellang.json");
        using var documento = JsonDocument.Parse(File.ReadAllText(ruta));
        var raiz = documento.RootElement;
        var simulacion = raiz.GetProperty("simulaciones")[0];
        int k = simulacion.GetProperty("personaje").GetInt32();
        var personaje = raiz.GetProperty("personajes")[k];
        string[] estados = Textos(personaje.GetProperty("estados"));
        string[] eventos = Textos(personaje.GetProperty("eventos"));
        var atributos = personaje.GetProperty("atributos").EnumerateArray()
            .Select(a => (nombre: a.GetProperty("nombre").GetString(), tipo: a.GetProperty("tipo").GetString()))
            .ToArray();

        int fallos = 0, n = 0;
        foreach (var paso in simulacion.GetProperty("pasos").EnumerateArray())
        {
            string evento = paso.GetProperty("evento").GetString();
            int error = n == 0 ? PixelLangNative.pl_iniciar(k)
                               : PixelLangNative.pl_evento(k, Array.IndexOf(eventos, evento));
            string esperado = paso.GetProperty("estado").GetString();
            int j = PixelLangNative.pl_estado(k);
            string estado = error != 0 ? "error" : (j >= 0 && j < estados.Length ? estados[j] : "?");
            bool coincide = esperado == "" ? error != 0 : estado == esperado;
            var valores = paso.GetProperty("valores").EnumerateArray().Select(v => v.GetDouble()).ToArray();
            var texto = new string[atributos.Length];
            for (int a = 0; a < atributos.Length && error == 0; a++)
            {
                double v = atributos[a].tipo == "entero" ? PixelLangNative.pl_entero(k, a)
                         : atributos[a].tipo == "real" ? PixelLangNative.pl_real(k, a)
                         : PixelLangNative.pl_logico(k, a);
                coincide &= a < valores.Length && Math.Abs(v - valores[a]) <= 1e-9 * Math.Max(1.0, Math.Abs(v));
                texto[a] = atributos[a].nombre + "=" + v.ToString(CultureInfo.InvariantCulture);
            }
            Console.WriteLine($"Paso {n,2}  {evento,-17} {estado,-10} {string.Join(" ", texto)}  {(coincide ? "coincide" : "DIFIERE")}");
            if (!coincide)
                fallos++;
            n++;
        }
        // Hay P personajes con instancias_por_personaje instancias cada uno: los números válidos
        // van de 0 a P·instancias - 1
        int personajes = raiz.GetProperty("personajes").GetArrayLength();
        int total = personajes * raiz.GetProperty("instancias_por_personaje").GetInt32();
        bool indices = PixelLangNative.pl_iniciar(-1) == 3 && PixelLangNative.pl_iniciar(total) == 3
                       && PixelLangNative.pl_evento(k, 999) == 3 && PixelLangNative.pl_estado(total) == -1;
        Console.WriteLine(indices ? $"Índices inválidos: rechazados con el código 3 (hay {total} instancias)"
                                  : "Índices inválidos: NO se rechazaron");
        if (!indices)
            fallos++;
        // La segunda instancia del personaje (k + P) tiene su propia ficha: iniciarla y enviarle
        // un evento no cambia a la primera
        int antes = PixelLangNative.pl_estado(k);
        int segunda = k + personajes;
        bool fichas = PixelLangNative.pl_iniciar(segunda) == 0 && PixelLangNative.pl_evento(segunda, 0) == 0
                      && PixelLangNative.pl_estado(segunda) != PixelLangNative.pl_estado(k)
                      && PixelLangNative.pl_estado(k) == antes;
        Console.WriteLine(fichas ? $"Instancias: la instancia {segunda} no cambia a la instancia {k}"
                                 : "Instancias: las fichas NO son independientes");
        if (!fichas)
            fallos++;
        Console.WriteLine($"C# con DllImport: {n} pasos comparados con la máquina de TAC, fallos: {fallos}");
        return fallos == 0 ? 0 : 1;
    }

    static string[] Textos(JsonElement arreglo)
    {
        return arreglo.EnumerateArray().Select(e => e.GetString()).ToArray();
    }
}
