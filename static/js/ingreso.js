// Mostrar la clave y avisar Bloq Mayús. Sin JavaScript, el formulario funciona igual.
(() => {
    const clave = document.querySelector('#form-ingreso input[name="password"]');
    const boton = document.getElementById('mostrar-clave');
    const aviso = document.getElementById('aviso-mayus');
    if (!clave || !boton || !aviso) return;

    boton.hidden = false;
    boton.addEventListener('click', () => {
        const mostrar = clave.type === 'password';
        clave.type = mostrar ? 'text' : 'password';
        boton.querySelector('.mostrar-texto').textContent = mostrar ? 'Ocultar' : 'Mostrar';
    });
    // Al enviar vuelve a ocultarla, para que el navegador la trate como contraseña.
    document.getElementById('form-ingreso').addEventListener('submit', () => { clave.type = 'password'; });

    const revisarMayus = (evento) => {
        const activo = evento.getModifierState && evento.getModifierState('CapsLock');
        const texto = activo ? 'Bloq Mayús está activado.' : '';
        if (aviso.textContent !== texto) aviso.textContent = texto;
    };
    clave.addEventListener('keydown', revisarMayus);
    clave.addEventListener('keyup', revisarMayus);
    clave.addEventListener('blur', () => { aviso.textContent = ''; });
})();
