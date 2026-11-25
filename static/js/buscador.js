// Filtra las tarjetas mientras se escribe; no distingue mayúsculas ni tildes.
(() => {
    const caja = document.getElementById('buscador');
    const q = document.getElementById('q');
    const resultado = document.getElementById('resultado');
    const vacio = document.getElementById('sin-resultados');
    const tarjetas = [...document.querySelectorAll('[data-buscar]')];
    const secciones = [...document.querySelectorAll('.seccion')];
    const normalizar = (texto) => texto.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    tarjetas.forEach((t) => { t.dataset.buscar = normalizar(t.dataset.buscar); });

    caja.hidden = false;
    q.addEventListener('input', () => {
        const termino = normalizar(q.value.trim());
        let visibles = 0;
        tarjetas.forEach((t) => {
            const coincide = !termino || t.dataset.buscar.includes(termino);
            t.hidden = !coincide;
            if (coincide) visibles++;
        });
        secciones.forEach((s) => { s.hidden = !s.querySelector('[data-buscar]:not([hidden])'); });
        vacio.hidden = visibles > 0;
        resultado.textContent = termino ? (visibles === 1 ? '1 herramienta encontrada.' : `${visibles} herramientas encontradas.`) : '';
    });
})();
