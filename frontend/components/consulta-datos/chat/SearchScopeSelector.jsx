import React from 'react';
import { Select, SelectItem, Input } from '@heroui/react';
import { IoDocument, IoGlobe } from 'react-icons/io5';

const SearchScopeSelector = ({ searchScope, setSearchScope, expedienteNumber, setExpedienteNumber }) => {
  return (
    <div className="mx-4 mb-2 flex items-center gap-2">
      {/* Selector compacto */}
      <Select
        value={searchScope}
        onSelectionChange={(value) => setSearchScope(value)}
        size="sm"
        variant="bordered"
        placeholder="Alcance"
        className="w-32"
        classNames={{
          trigger: "h-8 min-h-8 border-gray-300",
          value: "text-xs text-gray-700",
          listboxWrapper: "max-h-40"
        }}
        startContent={
          searchScope === 'general' ? (
            <IoGlobe className="w-3 h-3 text-gray-500" />
          ) : (
            <IoDocument className="w-3 h-3 text-gray-500" />
          )
        }
      >
        <SelectItem key="general" value="general" className="text-xs">
          <div className="flex items-center gap-2">
            <IoGlobe className="w-3 h-3" />
            <span>General</span>
          </div>
        </SelectItem>
        <SelectItem key="expediente" value="expediente" className="text-xs">
          <div className="flex items-center gap-2">
            <IoDocument className="w-3 h-3" />
            <span>Expediente</span>
          </div>
        </SelectItem>
      </Select>

      {/* Input para expediente - solo si está seleccionado */}
      {searchScope === 'expediente' && (
        <Input
          placeholder="Núm. expediente"
          value={expedienteNumber}
          onValueChange={setExpedienteNumber}
          size="sm"
          variant="bordered"
          className="flex-1 max-w-48"
          classNames={{
            input: "text-xs",
            inputWrapper: "h-8 min-h-8 border-gray-300"
          }}
        />
      )}
    </div>
  );
};

export default SearchScopeSelector;
