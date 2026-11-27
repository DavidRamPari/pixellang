using System.Runtime.InteropServices;

// Interfaz C de la biblioteca que genera el compilador de PixelLang (src/codigo_llvm.py).
// Los índices de personajes, eventos y atributos siguen el orden de declaración del programa;
// el archivo pixellang.json relaciona cada índice con su nombre. Las funciones que reciben o
// cambian al personaje devuelven un código de error: 0 sin error, 1 división entre cero,
// 2 desbordamiento de entero y 3 personaje, evento o atributo inválido.
public static class PixelLangNative
{
    const string Biblioteca = "pixellang";

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_iniciar(int personaje);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_evento(int personaje, int evento);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_estado(int personaje);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_error(int personaje);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_entero(int personaje, int atributo);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern double pl_real(int personaje, int atributo);

    [DllImport(Biblioteca, CallingConvention = CallingConvention.Cdecl)]
    public static extern int pl_logico(int personaje, int atributo);
}
