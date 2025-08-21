import React, { forwardRef } from 'react';
import classNames from 'classnames';

const Textarea = forwardRef(({ className, ...props }, ref) => {
  return (
    <textarea
      className={classNames(
        "flex min-h-[85px] w-full rounded-md border bg-white px-3 py-2 text-sm placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});

export { Textarea };
