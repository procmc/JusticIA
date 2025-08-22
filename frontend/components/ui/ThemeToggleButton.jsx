import React from 'react';
import { Button } from '@heroui/react';
import { IoSunny, IoMoon } from 'react-icons/io5';
import { useTheme } from '../../contexts/ThemeContext';

const ThemeToggleButton = () => {
  const { isDark, toggleTheme } = useTheme();

  return (
    <Button
      isIconOnly
      variant="ghost"
      size="sm"
      className="text-slate-600 hover:text-blue-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:text-blue-400 dark:hover:bg-slate-700 transition-all duration-200"
      onPress={toggleTheme}
      aria-label={isDark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
    >
      {isDark ? (
        <IoSunny className="w-4 h-4" />
      ) : (
        <IoMoon className="w-4 h-4" />
      )}
    </Button>
  );
};

export default ThemeToggleButton;
