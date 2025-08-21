import React from 'react';
import { 
  Card, 
  CardBody, 
  Tabs, 
  Tab, 
  Textarea, 
  Input, 
  Button 
} from '@heroui/react';
import { IoSearch, IoDocument, IoText } from 'react-icons/io5';

const SearchFilters = ({ 
  searchMode, 
  setSearchMode, 
  searchText, 
  setSearchText, 
  expedientNumber, 
  setExpedientNumber, 
  onSearch, 
  isSearching 
}) => {
  return (
    <Card className="mb-8">
      <CardBody className="p-6">
        <div className="space-y-6">
          {/* Tabs para modo de búsqueda */}
          <Tabs 
            selectedKey={searchMode} 
            onSelectionChange={setSearchMode}
            color="primary"
            variant="underlined"
            classNames={{
              tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
              cursor: "w-full bg-primary",
              tab: "max-w-fit px-0 h-12",
              tabContent: "group-data-[selected=true]:text-primary"
            }}
          >
            <Tab
              key="description"
              title={
                <div className="flex items-center space-x-2">
                  <IoText className="w-4 h-4" />
                  <span>Descripción del Caso</span>
                </div>
              }
            >
              <div className="mt-6">
                <Textarea
                  placeholder="Descripción del caso o situación legal"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  minRows={4}
                  className="max-w-md"
                />
              </div>
            </Tab>
            
            <Tab
              key="expedient"
              title={
                <div className="flex items-center space-x-2">
                  <IoDocument className="w-4 h-4" />
                  <span>Número de Expediente</span>
                </div>
              }
            >
              <div className="mt-6">
                <Input
                  placeholder="Ingresa el número de expediente (ej: 2024-001-01-CI)"
                  value={expedientNumber}
                  onChange={(e) => setExpedientNumber(e.target.value)}
                  className="max-w-md"
                />
              </div>
            </Tab>
          </Tabs>

          {/* Botón de Búsqueda */}
          <Button
            onClick={onSearch}
            color="primary"
            size="lg"
            startContent={<IoSearch className="w-5 h-5" />}
            isLoading={isSearching}
            className="w-full max-w-md"
          >
            Buscar Casos Similares
          </Button>
        </div>
      </CardBody>
    </Card>
  );
};

export default SearchFilters;
