
const FormContainer = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="w-full max-w-none">
      {children}
    </div>
  );
};

export default FormContainer;
