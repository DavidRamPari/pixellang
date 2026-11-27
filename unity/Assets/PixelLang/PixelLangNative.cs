using System.Runtime.InteropServices;

// Interfaz C de la biblioteca que genera el compilador de PixelLang (src/codigo_llvm.py).
// Los índices de personajes, eventos y atributos siguen el orden de declaración del programa;
// el archivo pixellang.json relaciona cada índice con su nombre.
//
// Cada personaje tiene varias instancias (instancias_por_personaje en el mapa, 64), y cada
// instancia tiene su ficha en la biblioteca: su estado y sus atributos. La instancia n del
// personaje p se elige con el número p + P·n, donde P es el número de personajes del
// programa; así, 0, 1, ..., P - 1 son la primera instancia de cada personaje.
//
// Las funciones que reciben o cambian una instancia devuelven un código de error: 0 sin
// error, 1 división entre cero, 2 desbordamiento de entero y 3 instancia, evento o atributo
// inválido.
public static class PixelLangNative
{
    const string Biblioteca = "pixellang";

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_iniciar(int instancia);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_evento(int instancia, int evento);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_estado(int instancia);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_error(int instancia);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_entero(int instancia, int atributo);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern double pl_real(int instancia, int atributo);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_logico(int instancia, int atributo);
}
