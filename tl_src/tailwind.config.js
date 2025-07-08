module.exports = {
  purge: {
    content: ['../app/templates/**/*.html', '../app/static/js/*.js'],
    options: {
      safelist: ["pt-8", "py-2", "pt-6", "px-6", "px-8", "md:px-8", "lg:px-10", "bg-error"]
    }
  },
  theme: {
    extend: {
      fontSize: {
        h1: ['1.75rem', { lineHeight: '2rem' }],
        h2: ['1.5rem', { lineHeight: '1.75rem' }],
        h3: ['1.25rem', { lineHeight: '1.5rem' }],
        h4: ['1.15rem', { lineHeight: '1.25rem' }],
        xs: ['0.7rem', { lineHeight: '1rem' }],
        base: ['0.75rem', { lineHeight: '1.15rem' }],
        sm: ['0.75rem', { lineHeight: '1.15rem' }],
        lg: ['0.9rem', { lineHeight: '1.4rem' }],
        xl: ['1.125rem', { lineHeight: '1.6rem' }],
        "2xl": ['1.25rem', { lineHeight: '1.8rem' }],
      },
      colors: {
        'base-400': '#e5e5e5'
      },
    }
  },
  plugins: [require("@tailwindcss/typography"), require("daisyui"), require("@harshtalks/slash-tiptap")],
  daisyui: {
    themes: [
        {
          light: {
            "color-scheme": "light",
            "primary": "#3b82f6",
            "primary-content": "#f1f1f1",
            "success-content": "#2d3036",
            "warning-content": "#2d3036",
            "error-content": "#2d3036",
            "secondary": "#2563EB",
            "secondary-content": "oklch(98.71% 0.0106 342.55)",
            "accent": "#f68067",
            "neutral-content": "#d7dde4",
            "neutral": "#2b3440",
            "base-100": "#fff",
            "base-200": "#f9fafb",
            "base-300": "#f2f4f7",
            "base-400": "#e5e5e5",
            "base-content": "#394E6A",
            "info": "#55cbd3",
            "success": "#22c55e",
            "warning": "#eab308",
            "error": "#ef4444"
          }
       },
       {
          dark: {
            "color-scheme": "dark",
            "primary": "#3b82f6",
            "primary-content": "#cccccc",
            "success-content": "#2d3036",
            "warning-content": "#2d3036",
            "error-content": "#2d3036",
            "secondary": "#66cc8a",
            "accent": "#f68067",
            "neutral-content": "#B2CCD6",
            "base-100": "#2A303C",
            "base-200": "#242933",
            "base-300": "#20252E",
            "base-400": "#e5e5e5",
            "base-content": "#B2CCD6",
            "info": "#55cbd3",
            "success": "#22c55e",
            "warning": "#eab308",
            "error": "#fc605f",
          }
       }
    ]
  },
};
