using System.Collections.Generic;
using UnityEngine;

// Dibujos en pixel art de la escena: el caballero, el slime, el tajo de la espada y una
// estrella de aturdimiento. Se crean al ejecutar, a partir de cuadrículas de caracteres.
public static class DibujosPixelLang
{
    static readonly string[] CaballeroDibujo =
    {
        "................",
        ".....KKKKKK.....",
        "....KSSSSSSK..W.",
        "....KSVVVVSK..W.",
        "....KSSSSSSK..W.",
        ".....KSSSSK...W.",
        "...KKAAAAAAKKHHH",
        "..KAAAAAAAAAAKH.",
        "..KAAAYYYYAAAK..",
        "..KAAAAAAAAAAK..",
        "...KKAAAAAAKK...",
        "....KAAAAAAK....",
        "....KAAK..KAAK..",
        "....KBBK..KBBK..",
        "...KBBBK..KBBBK.",
        "................",
    };

    static readonly string[] SlimeDibujo =
    {
        "......GGGG......",
        "....GGLLLLGG....",
        "...GLLLLLLLLG...",
        "..GLLLLLLLLLLG..",
        "..GLLWKLLWKLLG..",
        ".GLLLWKLLWKLLLG.",
        ".GLLLLLLLLLLLLG.",
        "GLLLLLLLLLLLLLLG",
        "GLLLLLLLLLLLLLLG",
        ".GGGGGGGGGGGGGG.",
    };

    static readonly string[] TajoDibujo =
    {
        "...WC.....",
        ".....WC...",
        "......WC..",
        ".......WC.",
        ".......WWC",
        "........WC",
        "........WC",
        "........WC",
        "........WC",
        ".......WWC",
        ".......WC.",
        "......WC..",
        ".....WC...",
        "...WC.....",
    };

    static readonly string[] EstrellaDibujo =
    {
        "..Y..",
        ".YYY.",
        "YYYYY",
        ".YYY.",
        "..Y..",
    };

    static readonly Dictionary<char, Color> Paleta = new Dictionary<char, Color>
    {
        { 'K', new Color(0.08f, 0.08f, 0.12f) }, { 'S', new Color(0.74f, 0.77f, 0.82f) },
        { 'V', new Color(0.16f, 0.16f, 0.22f) }, { 'A', new Color(0.24f, 0.45f, 0.86f) },
        { 'Y', new Color(0.96f, 0.80f, 0.22f) }, { 'W', new Color(0.95f, 0.96f, 1.00f) },
        { 'H', new Color(0.55f, 0.36f, 0.16f) }, { 'B', new Color(0.36f, 0.25f, 0.18f) },
        { 'G', new Color(0.09f, 0.33f, 0.16f) }, { 'L', new Color(0.40f, 0.80f, 0.36f) },
        { 'C', new Color(0.62f, 0.85f, 1.00f) },
    };

    public static Sprite Caballero() { return Crear(CaballeroDibujo, new Vector2(0.5f, 0f), 8f); }
    public static Sprite Slime() { return Crear(SlimeDibujo, new Vector2(0.5f, 0f), 8f); }
    public static Sprite Tajo() { return Crear(TajoDibujo, new Vector2(0f, 0.5f), 8f); }
    public static Sprite Estrella() { return Crear(EstrellaDibujo, new Vector2(0.5f, 0.5f), 16f); }

    public static Sprite DeColor(Color color)
    {
        var textura = new Texture2D(1, 1) { filterMode = FilterMode.Point };
        textura.SetPixel(0, 0, color);
        textura.Apply();
        return Sprite.Create(textura, new Rect(0, 0, 1, 1), new Vector2(0.5f, 0.5f), 1f);
    }

    // Colinas del fondo: columnas de distinta altura, como un paisaje de pixel art
    public static Sprite Colinas(Color color, int semilla)
    {
        const int ancho = 96, alto = 24;
        var textura = new Texture2D(ancho, alto, TextureFormat.RGBA32, false)
        {
            filterMode = FilterMode.Point,
            wrapMode = TextureWrapMode.Clamp,
        };
        for (int x = 0; x < ancho; x++)
        {
            float h = 10f + 6f * Mathf.Sin((x + semilla) * 0.13f) + 4f * Mathf.Sin((x + 3 * semilla) * 0.31f);
            for (int y = 0; y < alto; y++)
                textura.SetPixel(x, y, y < h ? color : Color.clear);
        }
        textura.Apply();
        return Sprite.Create(textura, new Rect(0, 0, ancho, alto), new Vector2(0.5f, 0f), 4f);
    }

    static Sprite Crear(string[] dibujo, Vector2 pivote, float pixelesPorUnidad)
    {
        int alto = dibujo.Length, ancho = dibujo[0].Length;
        var textura = new Texture2D(ancho, alto, TextureFormat.RGBA32, false)
        {
            filterMode = FilterMode.Point,
            wrapMode = TextureWrapMode.Clamp,
        };
        for (int fila = 0; fila < alto; fila++)
            for (int col = 0; col < ancho; col++)
            {
                char c = dibujo[fila][col];
                textura.SetPixel(col, alto - 1 - fila, c == '.' ? Color.clear : Paleta[c]);
            }
        textura.Apply();
        return Sprite.Create(textura, new Rect(0, 0, ancho, alto), pivote, pixelesPorUnidad);
    }
}
