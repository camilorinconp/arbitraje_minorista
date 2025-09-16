// frontend/src/components/FormularioMinorista.test.tsx

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FormularioMinorista from './FormularioMinorista';

// Mock de la API para evitar llamadas reales durante el test
jest.mock('../api/gestionDatosApi', () => ({
  createMinorista: jest.fn(),
}));

describe('FormularioMinorista', () => {
  test('debe renderizar el formulario con todos los campos', () => {
    render(<FormularioMinorista />);

    // Verificar que el título y los campos de texto principales estén presentes
    expect(screen.getByText(/Añadir Nuevo Minorista/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nombre del Minorista/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/URL Base/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Activo para Scrapeo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Selector CSS para Nombre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Selector CSS para Precio/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Selector CSS para Imagen/i)).toBeInTheDocument();

    // Verificar que el botón de envío exista
    expect(screen.getByRole('button', { name: /Guardar Minorista/i })).toBeInTheDocument();
  });

  test('debe permitir al usuario escribir en los campos de texto', () => {
    render(<FormularioMinorista />);

    const nombreInput = screen.getByLabelText(/Nombre del Minorista/i) as HTMLInputElement;
    const urlInput = screen.getByLabelText(/URL Base/i) as HTMLInputElement;

    fireEvent.change(nombreInput, { target: { value: 'Nuevo Minorista de Prueba' } });
    fireEvent.change(urlInput, { target: { value: 'https://test.com' } });

    expect(nombreInput.value).toBe('Nuevo Minorista de Prueba');
    expect(urlInput.value).toBe('https://test.com');
  });

  test('el switch de "Activo" debe poder cambiarse', () => {
    render(<FormularioMinorista />);

    const switchInput = screen.getByLabelText(/Activo para Scrapeo/i) as HTMLInputElement;

    // Por defecto está activado
    expect(switchInput.checked).toBe(true);

    // Simular click para desactivarlo
    fireEvent.click(switchInput);
    expect(switchInput.checked).toBe(false);
  });
});
