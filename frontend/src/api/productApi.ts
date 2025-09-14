// frontend/src/api/productApi.ts

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export interface Product {
  id: number;
  name: string;
  price: number;
  product_url: string;
  image_url: string | null;
  last_scraped_at: string; // ISO string date
}

export const getProducts = async (): Promise<Product[]> => {
  try {
    const response = await axios.get<Product[]>(`${API_BASE_URL}/products/`);
    return response.data;
  } catch (error) {
    console.error("Error fetching products:", error);
    throw error;
  }
};
