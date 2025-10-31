import React from 'react';
import { useRouter } from 'next/router';
import Bitacora from '@/components/administracion/bitacora/Bitacora';

const BitacoraPage = () => {
  const router = useRouter();
  const { tab, scroll } = router.query;

  return (
    <>
      <Bitacora initialTab={tab} scrollTarget={scroll} />
    </>
  );
};

export default BitacoraPage;
