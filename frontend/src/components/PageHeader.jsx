import React from "react";
import Tabs from "./Tabs";

export default function PageHeader({
  title,
  subtitle,
  eyebrow,
  primaryAction,
  secondaryActions,
  actions,
  tabs,
  activeTab,
  onTabChange,
  children,
}) {
  return (
    <div className="pageHeader">
      <div className="pageHeaderMain">
        <div className="pageHeaderCopy">
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          {title && <h1>{title}</h1>}
          {subtitle && <p className="pageHeaderSubtitle">{subtitle}</p>}
        </div>

        {(primaryAction || secondaryActions || actions) && (
          <div className="pageHeaderActions">
            {secondaryActions}
            {actions}
            {primaryAction}
          </div>
        )}
      </div>

      {tabs && (
        <div className="pageHeaderTabs">
          {Array.isArray(tabs) ? (
            <Tabs
              tabs={tabs}
              activeTab={activeTab}
              onChange={onTabChange}
            />
          ) : (
            tabs
          )}
        </div>
      )}

      {children}
    </div>
  );
}
