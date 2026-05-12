/**
 * Catalogo de categorias de Kit Digital que ofrecemos en la landing.
 *
 * El backend (`POST /elegibilidad`) espera un codigo de 2 digitos ("01"–"14")
 * que es el ID oficial de la convocatoria de Red.es. La landing muestra una
 * etiqueta humana al usuario.
 *
 * Si en el futuro se anade/quita una categoria, basta con tocar este array.
 */

export const ELIGIBILITY_CATEGORIAS = [
  {
    codigo: '04',
    label: 'Gestión de Clientes (CRM)',
    descripcion: 'Programa para organizar contactos, oportunidades y ventas.',
  },
  {
    codigo: '07',
    label: 'Factura Electrónica',
    descripcion: 'Solución de facturación digital adaptada a Verifactu.',
  },
  {
    codigo: '01',
    label: 'Sitio Web y Presencia en Internet',
    descripcion: 'Web profesional con dominio, hosting y SEO básico.',
  },
  {
    codigo: '02',
    label: 'Comercio Electrónico (Tienda online)',
    descripcion: 'Tienda online con pasarela de pago y catálogo.',
  },
  {
    codigo: '14',
    label: 'Puesto de Trabajo Seguro',
    descripcion: 'Portátil + protección y configuración profesional.',
  },
]

export function getCategoriaByCodigo(codigo) {
  return ELIGIBILITY_CATEGORIAS.find((c) => c.codigo === codigo) ?? null
}

export function getLabelByCodigo(codigo) {
  return getCategoriaByCodigo(codigo)?.label ?? `Categoría ${codigo}`
}
