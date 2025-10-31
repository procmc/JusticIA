import React from 'react';
import { useRouter } from 'next/router';
import ConsultaChat from '../../../components/consulta-datos/chat/Chat';

const ConsultaChatPage = () => {
  const router = useRouter();
  const { mode } = router.query;

  return (
    <ConsultaChat initialMode={mode} />
  );
};

export default ConsultaChatPage;
