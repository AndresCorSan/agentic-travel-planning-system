// PrimeVue Aura preset customized for the app: warm surface scale plus
// small component radii. Default brand = the sunset accent (accents.ts).
import Aura from '@primeuix/themes/aura';
import { definePreset } from '@primeuix/themes';
import { ACCENTS } from './accents';

// Default brand scale = the 'sunset' accent (single source in accents.ts).
// The accent selector overrides --p-primary-* at runtime. Border radius
// kept small (no pill UI).
const sunset = ACCENTS.find((a) => a.id === 'sunset')?.scale ?? {
  50: '#fff7ed',
  100: '#ffedd5',
  200: '#fed7aa',
  300: '#fdba74',
  400: '#fb923c',
  500: '#f97316',
  600: '#ea580c',
  700: '#c2410c',
  800: '#9a3412',
  900: '#7c2d12',
  950: '#431407'
};

export const TravelPreset = definePreset(Aura, {
  primitive: {
    brand: { ...sunset }
  },
  semantic: {
    primary: {
      50: '{brand.50}',
      100: '{brand.100}',
      200: '{brand.200}',
      300: '{brand.300}',
      400: '{brand.400}',
      500: '{brand.500}',
      600: '{brand.600}',
      700: '{brand.700}',
      800: '{brand.800}',
      900: '{brand.900}',
      950: '{brand.950}'
    },
    colorScheme: {
      light: {
        surface: {
          0: '#faf9f7',
          50: '#f4f2ee',
          100: '#e9e6e0',
          200: '#d9d4cb',
          300: '#bfb8ab',
          400: '#a29a8a',
          500: '#857d6f',
          600: '#6a6459',
          700: '#55514a',
          800: '#47443e',
          900: '#3d3b36',
          950: '#211f1c'
        }
      },
      dark: {
        surface: {
          0: '#16181d',
          50: '#1c1f26',
          100: '#242832',
          200: '#2f3541',
          300: '#3d4452',
          400: '#545d6f',
          500: '#6b7488',
          600: '#8b93a7',
          700: '#aab1c2',
          800: '#c8cdda',
          900: '#e2e5ec',
          950: '#f4f5f8'
        }
      }
    }
  },
  components: {
    button: {
      root: { borderRadius: '8px' }
    },
    inputtext: {
      root: { borderRadius: '10px' }
    },
    textarea: {
      root: { borderRadius: '10px' }
    },
    card: {
      root: { borderRadius: '10px' }
    },
    message: {
      root: { borderRadius: '8px' }
    }
  }
});
