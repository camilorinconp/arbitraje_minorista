// frontend/src/api/gestionDatosApi.ts

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

// --- Interfaces ---

export interface MinoristaBase {
  nombre: string;
  url_base: string;
  activo?: boolean;
  name_selector?: string | null;
  price_selector?: string | null;
  image_selector?: string | null;
}

export interface Minorista {
  id: number;
  nombre: string;
  url_base: string;
  activo: boolean;
  created_at: string; // ISO string date
  name_selector: string | null;
  price_selector: string | null;
  image_selector: string | null;
}

export interface Producto {
  id: number;
  nombre: string;
  precio: number;
  url_producto: string;
  url_imagen: string | null;
  ultima_fecha_rastreo: string; // ISO string date
  fecha_creacion: string; // ISO string date
  id_minorista: number;
  identificador_producto: string | null;
  minorista?: Minorista; // Opcional, si se carga la relación
}

export interface HistorialPrecio {
  id: number;
  id_producto: number;
  id_minorista: number;
  precio: number;
  fecha_registro: string; // ISO string date
}

// --- Funciones de API ---

// Productos
export const getProductos = async (): Promise<Producto[]> => {
  try {
    const response = await axios.get<Producto[]>(`${API_BASE_URL}/gestion-datos/productos/`);
    return response.data;
  } catch (error) {
    console.error("Error al obtener productos:", error);
    throw error;
  }
};

export const getHistorialPreciosProducto = async (productoId: number): Promise<HistorialPrecio[]> => {
  try {
    const response = await axios.get<HistorialPrecio[]>(`${API_BASE_URL}/gestion-datos/productos/${productoId}/historial-precios`);
    return response.data;
  } catch (error) {
    console.error(`Error al obtener historial de precios para el producto ${productoId}:`, error);
    throw error;
  }
};

// Minoristas
export const getMinoristas = async (): Promise<Minorista[]> => {
  try {
    const response = await axios.get<Minorista[]>(`${API_BASE_URL}/gestion-datos/minoristas/`);
    return response.data;
  } catch (error) {
    console.error("Error al obtener minoristas:", error);
    throw error;
  }
};

export const createMinorista = async (minoristaData: MinoristaBase): Promise<Minorista> => {
  try {
    const response = await axios.post<Minorista>(`${API_BASE_URL}/gestion-datos/minoristas/`, minoristaData);
    return response.data;
  } catch (error) {
    console.error("Error al crear minorista:", error);
    throw error;
  }
};

// Scraper
export const activarScraper = async (urlProducto: string, idMinorista: number): Promise<Producto> => {
  try {
    const response = await axios.post<Producto>(`${API_BASE_URL}/gestion-datos/scrape/`, {
      url_producto: urlProducto,
      id_minorista: idMinorista,
    });
    return response.data;
  } catch (error) {
    console.error("Error al activar scraper:", error);
    throw error;
  }
};