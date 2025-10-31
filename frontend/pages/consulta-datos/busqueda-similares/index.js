import React from 'react';
import { useRouter } from 'next/router';
import BusquedaSimilares from '@/components/consulta-datos/busqueda-similares/BusquedaSimilares';

const BusquedaSimilaresPage = () => {
  const router = useRouter();
  const { mode } = router.query;

  return (
    <>
      <BusquedaSimilares initialMode={mode} />
    </>
  );
};

export default BusquedaSimilaresPage;
