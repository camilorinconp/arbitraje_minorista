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
  discovery_url?: string | null;
  product_link_selector?: string | null;
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
  discovery_url: string | null;
  product_link_selector: string | null;
}

export interface Producto {
  id: number;
  name: string;
  price: number;
  product_url: string;
  image_url: string | null;
  last_scraped_at: string; // ISO string date
  created_at: string; // ISO string date
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

export const updateMinorista = async (id: number, minoristaData: MinoristaBase): Promise<Minorista> => {
  try {
    const response = await axios.put<Minorista>(`${API_BASE_URL}/gestion-datos/minoristas/${id}`, minoristaData);
    return response.data;
  } catch (error) {
    console.error(`Error al actualizar minorista con ID ${id}:`, error);
    throw error;
  }
};

export const deleteMinorista = async (id: number): Promise<void> => {
  try {
    await axios.delete(`${API_BASE_URL}/gestion-datos/minoristas/${id}`);
  } catch (error) {
    console.error(`Error al eliminar minorista con ID ${id}:`, error);
    throw error;
  }
};

// Scraper
export const runScraper = async (product_url: string, id_minorista: number): Promise<Producto> => {
  try {
    const response = await axios.post<Producto>(`${API_BASE_URL}/scraper/run/`, {
      product_url,
      id_minorista,
    });
    return response.data;
  } catch (error) {
    console.error("Error al ejecutar el scraper:", error);
    throw error;
  }
};