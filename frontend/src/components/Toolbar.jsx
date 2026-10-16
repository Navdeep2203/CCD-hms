import React from "react";

export default function Toolbar({
  search,
  onSearchChange,
  onSearchSubmit,
  searchPlaceholder = "Search...",
  filters,
  actions,
  children,
  className = "",
}) {
  const hasConfigSearch = search !== undefined || onSearchSubmit !== undefined;

  return (
    <div className={`toolbar ${className}`.trim()}>
      {hasConfigSearch && (
        <form
          className="toolbarSearchForm"
          onSubmit={(e) => {
            e.preventDefault();
            onSearchSubmit?.(search);
          }}
        >
          <div className="toolbarSearchInputWrapper">
            <span className="toolbarSearchIcon" aria-hidden="true">
              🔍
            </span>
            <input
              type="search"
              className="toolbarSearchInput"
              value={search ?? ""}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder={searchPlaceholder}
            />
          </div>
          {onSearchSubmit && (
            <button type="submit" className="secondary btn-sm">
              Search
            </button>
          )}
        </form>
      )}

      {filters && <div className="toolbarFilters">{filters}</div>}

      {children && <div className="toolbarContent">{children}</div>}

      {actions && <div className="toolbarActions">{actions}</div>}
    </div>
  );
}
