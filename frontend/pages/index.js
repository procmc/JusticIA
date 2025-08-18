export default function Home() {
  
  return (
    <div className="fixed inset-0 w-full h-full bg-white flex items-center justify-center z-0 overflow-hidden">
      <div
        className="relative z-10 rounded-[2.5rem] shadow-2xl flex flex-col items-center p-6 md:p-12 max-w-xl w-full animate-fade-in-down border border-white/40 backdrop-blur-xl bg-white/80"
        style={{
          background: 'linear-gradient(120deg,rgba(255,255,255,0.96) 80%,rgba(96,165,250,0.08) 100%)',
          boxShadow: '0 8px 40px 0 rgba(31, 38, 135, 0.12), 0 2px 16px 0 #2563eb18',
          border: '1.5px solid rgba(255,255,255,0.5)',
          maxHeight: 'calc(100vh - 32px)',
          overflow: 'hidden',
        }}
      >
        <h1 className="text-2xl md:text-3xl font-extrabold text-azulOscuro text-center drop-shadow-lg tracking-tight animate-fade-in-scale">
          ¡Holaaaa!
        </h1>
      </div>
    </div>
  );
}
