/* Configuração Tailwind compartilhada — carregar logo depois de cdn.tailwindcss.com */
window.tailwind = window.tailwind || {};
tailwind.config = {
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                lect: {
                    navy: '#0C1A2A', teal: '#009988', tealDark: '#00756C', tealLight: '#00B4A2',
                    orange: '#F39200', bgDark: '#060D17', cardDark: '#0B1626', borderDark: '#1E293B'
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
                display: ['Space Grotesk', 'sans-serif']
            }
        }
    }
};
