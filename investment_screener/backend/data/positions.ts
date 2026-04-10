import type { QuestradePosition } from '../types/index.ts';

export let positions: QuestradePosition[] = [];

export const updatePositions = (newPositions: QuestradePosition[]) => {
  positions = newPositions;
};

export const getPositions = (): QuestradePosition[] => {
  return positions;
};
