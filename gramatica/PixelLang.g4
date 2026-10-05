grammar PixelLang;

programa    : personaje+ simulacion* EOF ;

personaje   : PERSONAJE ID LLAVE_A atributo* eventos estado+ LLAVE_C ;

atributo    : ID DOS_PUNTOS tipo ASIGNA expr PUNTO_COMA ;
tipo        : ENTERO | REAL | LOGICO ;

eventos     : EVENTOS ID (COMA ID)* PUNTO_COMA ;

estado      : modificador? ESTADO ID LLAVE_A alEntrar? transicion* LLAVE_C ;
modificador : INICIAL | FINAL ;
alEntrar    : AL_ENTRAR bloque ;

transicion  : CUANDO ID guarda? FLECHA ID PUNTO_COMA ;
guarda      : SI expr ;

bloque      : LLAVE_A sentencia* LLAVE_C ;
sentencia   : ID ASIGNA expr PUNTO_COMA                 # asignacion
            | SI expr bloque (SINO bloque)?             # seleccion
            ;

simulacion  : SIMULAR ID DOS_PUNTOS ID (COMA ID)* PUNTO_COMA ;

expr        : conj (O_LOGICO conj)* ;
conj        : rel (Y_LOGICO rel)* ;
rel         : arit (opRel arit)? ;
opRel       : MENOR | MAYOR | MENOR_IGUAL | MAYOR_IGUAL | IGUAL | DISTINTO ;
arit        : term ((MAS | MENOS) term)* ;
term        : unario ((POR | ENTRE) unario)* ;
unario      : (NO_LOGICO | MENOS) unario | factor ;
factor      : PAR_A expr PAR_C
            | NUM_ENTERO
            | NUM_REAL
            | VERDADERO
            | FALSO
            | ID
            ;

PERSONAJE   : 'personaje' ;
EVENTOS     : 'eventos' ;
ESTADO      : 'estado' ;
INICIAL     : 'inicial' ;
FINAL       : 'final' ;
AL_ENTRAR   : 'al_entrar' ;
CUANDO      : 'cuando' ;
SI          : 'si' ;
SINO        : 'sino' ;
SIMULAR     : 'simular' ;
ENTERO      : 'entero' ;
REAL        : 'real' ;
LOGICO      : 'logico' | 'l\u00F3gico' ;
VERDADERO   : 'verdadero' ;
FALSO       : 'falso' ;

FLECHA      : '->' ;
O_LOGICO    : '||' ;
Y_LOGICO    : '&&' ;
IGUAL       : '==' ;
DISTINTO    : '!=' ;
MENOR_IGUAL : '<=' ;
MAYOR_IGUAL : '>=' ;
MENOR       : '<' ;
MAYOR       : '>' ;
NO_LOGICO   : '!' ;
ASIGNA      : '=' ;
MAS         : '+' ;
MENOS       : '-' ;
POR         : '*' ;
ENTRE       : '/' ;

PAR_A       : '(' ;
PAR_C       : ')' ;
LLAVE_A     : '{' ;
LLAVE_C     : '}' ;
DOS_PUNTOS  : ':' ;
PUNTO_COMA  : ';' ;
COMA        : ',' ;

NUM_REAL    : DIGITO+ '.' DIGITO+ ;
NUM_ENTERO  : DIGITO+ ;
ID          : LETRA (LETRA | DIGITO)* ;

COMENTARIO_LINEA  : '//' ~[\r\n]* -> skip ;
COMENTARIO_BLOQUE : '/*' .*? '*/' -> skip ;
ESPACIOS          : [ \t\r\n]+ -> skip ;

fragment DIGITO : [0-9] ;
fragment LETRA  : [a-zA-Z_\u00E1\u00E9\u00ED\u00F3\u00FA\u00C1\u00C9\u00CD\u00D3\u00DA\u00F1\u00D1\u00FC\u00DC] ;
