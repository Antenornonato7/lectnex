// Configuração do Tailwind (CSS compilado em assets/tailwind.css).
// O GitHub Actions recompila sozinho a cada mudança em .html ou assets/*.js (workflow "Compilar CSS").
module.exports = {
    darkMode: 'class',
    content: ['./*.html', './assets/*.js'],
    theme: {
        extend: {
            colors: {
                lect: {
                    navy: '#0C1A2A', teal: '#009988', tealDark: '#00756C', tealLight: '#00B4A2',
                    orange: '#F39200', bgDark: '#060D17', cardDark: '#0B1626', borderDark: '#1E293B'
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
                display: ['Space Grotesk', 'Inter', 'sans-serif']
            }
        }
    }
};
